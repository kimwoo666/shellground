"""Real Jupyter client service; runs as learner only inside the owned guest.

One dedicated executor owns all ZeroMQ sockets. Socket requests merely submit
work or wait on a Future. Interrupt never waits behind an executing cell.
"""
import ast
import concurrent.futures
import json
import os
from pathlib import Path
import queue
import re
import signal
import socket
import socketserver
import sys
import threading
import time
import uuid

SOCKET = '/home/learner/.shellground-notebook.sock'
WORK = Path('/home/learner/notebook-work')
ENVS = Path('/home/learner/notebook-envs')
KERNELS = Path('/home/learner/notebook-jupyter/share/jupyter/kernels')
MAX_FRAME = 3 * 1024 * 1024


class Notebook:
    def __init__(self, workdir=None):
        from jupyter_client.kernelspec import KernelSpecManager
        self.specs = KernelSpecManager(kernel_dirs=[str(KERNELS)], ensure_native_kernel=False)
        self.manager = self.client = None
        self.selected = None
        self.generation = None
        self.cells = {}
        self.restart_count = 0
        self.restarts = {}
        self.starts = {}
        self.workdir = str(workdir or WORK)

    def kernels(self):
        result = []
        for name, entry in self.specs.get_all_specs().items():
            spec = entry['spec']; argv = spec['argv']
            # This is a teaching VM, but never launch an unrelated interpreter
            # merely because a user kernelspec points to it.
            if not argv or argv[0] not in [str(ENVS / n / 'bin/python') for n in ('basic', 'data')]:
                continue
            if 'ipykernel_launcher' not in argv:
                continue
            result.append(dict(name=name, display_name=spec['display_name'], executable=argv[0],
                               resource_dir=entry['resource_dir']))
        return sorted(result, key=lambda entry: entry['name'])

    def stop(self):
        if self.client:
            self.client.stop_channels()
            self.client = None
        if self.manager:
            try:
                self.manager.shutdown_kernel(now=True)
            finally:
                self.manager = None
        self.selected = self.generation = None

    def select(self, name):
        from jupyter_client import KernelManager
        if name not in {entry['name'] for entry in self.kernels()}:
            raise ValueError('등록된 학습용 커널을 찾을 수 없습니다. 목록을 새로 고치세요.')
        if self.selected == name and self.manager and self.manager.is_alive():
            return self.identity()
        self.stop()
        runtime = WORK / '.runtime'
        runtime.mkdir(mode=0o700, exist_ok=True)
        self.manager = KernelManager(kernel_name=name, kernel_spec_manager=self.specs,
            connection_file=str(runtime / ('kernel-' + uuid.uuid4().hex + '.json')),
            ip='127.0.0.1', shutdown_wait_time=2)
        # Do not leak the controller's shared library path into the selected
        # Python: each kernel must import its own installed packages.
        env = {key: value for key, value in os.environ.items() if key not in ('PYTHONPATH', 'PYTHONHOME')}
        self.manager.start_kernel(cwd=self.workdir, env=env)
        try:
            self.client = self.manager.blocking_client()
            self.client.start_channels()
            self.client.wait_for_ready(timeout=20)
            self.selected, self.generation = name, uuid.uuid4().hex
            result = self.identity()
            prefix = result['values']['prefix']
            self.starts[prefix] = self.starts.get(prefix,0)+1
            result['starts'] = dict(self.starts)
            return result
        except BaseException:
            self.stop()
            raise

    def restart(self):
        if not self.selected:
            raise RuntimeError('먼저 커널을 선택하세요.')
        name = self.selected
        prefix = str(Path(self.manager.kernel_spec.argv[0]).parent.parent)
        self.stop()
        result = self.select(name)
        self.restart_count += 1
        self.restarts[prefix] = self.restarts.get(prefix,0)+1
        result['restart_count'] = self.restart_count
        result['restarts'] = dict(self.restarts)
        return result

    def interrupt(self):
        manager = self.manager
        if manager and manager.provisioner and manager.provisioner.pid:
            try:
                os.kill(manager.provisioner.pid, signal.SIGINT)
            except ProcessLookupError:
                pass

    def exchange(self, code='', expressions=None, timeout=10, history=True):
        if not self.client or not self.manager or not self.manager.is_alive():
            raise RuntimeError('커널이 실행 중이 아닙니다. 커널을 다시 선택하세요.')
        msg_id = self.client.execute(code, silent=not history, store_history=history,
                                     user_expressions=expressions or {}, allow_stdin=False,
                                     stop_on_error=True)
        deadline = time.monotonic() + timeout
        reply = None; idle = False; messages = []; used = 0; truncated = False; interrupted = False
        while not (reply is not None and idle):
            if time.monotonic() > deadline:
                if interrupted:
                    self.stop()
                    raise TimeoutError('커널이 중단 요청에 응답하지 않아 종료했습니다. 셀 코드는 유지됩니다.')
                self.interrupt(); interrupted = True; deadline = time.monotonic() + 3
            try:
                message = self.client.get_iopub_msg(timeout=.05)
            except queue.Empty:
                message = None
            if message and message.get('parent_header', {}).get('msg_id') == msg_id:
                kind = message['msg_type']; content = message['content']
                if kind == 'status' and content.get('execution_state') == 'idle':
                    idle = True
                elif kind in ('stream', 'execute_result', 'display_data', 'error', 'clear_output'):
                    record = dict(type=kind, content=content)
                    size = len(json.dumps(record).encode())
                    if used + size <= 250000:
                        messages.append(record); used += size
                    else:
                        truncated = True
            if reply is None:
                try:
                    candidate = self.client.get_shell_msg(timeout=0)
                except queue.Empty:
                    candidate = None
                if candidate and candidate.get('parent_header', {}).get('msg_id') == msg_id:
                    reply = candidate['content']
        return dict(ok=reply.get('status') == 'ok', reply=reply, messages=messages,
                    execution_count=reply.get('execution_count'), truncated=truncated,
                    timed_out=interrupted, kernel=self.selected, generation=self.generation)

    def snapshot(self, expressions):
        if not isinstance(expressions, dict) or len(expressions) > 40:
            raise ValueError('Invalid kernel inspection')
        encoded = {key: '__import__("json").dumps((' + expression + '), ensure_ascii=False, '
                   'default=lambda v: v.item() if hasattr(v, "item") else repr(v))'
                   for key, expression in expressions.items()}
        response = self.exchange(expressions=encoded, history=False)
        values, errors = {}, {}
        for key, result in response['reply'].get('user_expressions', {}).items():
            if result.get('status') == 'ok':
                values[key] = json.loads(ast.literal_eval(result['data']['text/plain']))
            else:
                errors[key] = dict(ename=result.get('ename'), evalue=result.get('evalue'))
        return dict(values=values, errors=errors, kernel=self.selected, generation=self.generation)

    def identity(self):
        result = self.snapshot(dict(executable='__import__("sys").executable',
            prefix='__import__("sys").prefix', pid='__import__("os").getpid()',
            version='__import__("sys").version.split()[0]',
            numpy='__import__("importlib.util", fromlist=["find_spec"]).find_spec("numpy") is not None'))
        result.update(restart_count=self.restart_count, restarts=dict(self.restarts),
                      starts=dict(self.starts), kernels=self.kernels())
        if result['values'].get('pid') != self.manager.provisioner.pid:
            raise RuntimeError('Kernel identity did not match the actual process')
        return result

    def execute(self, cell_id, code):
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', cell_id) or not isinstance(code, str) or len(code) > 100000:
            raise ValueError('Invalid notebook cell')
        result = self.exchange(code)
        self.cells[cell_id] = dict(source=code, result=result)
        return result

    def save(self, filename, cells):
        import nbformat
        if not isinstance(filename, str) or Path(filename).name != filename or not filename.endswith('.ipynb'):
            raise ValueError('실습 폴더의 .ipynb 이름을 지정하세요.')
        path = WORK / filename
        if path.is_symlink(): raise ValueError('Notebook path cannot be a symlink')
        if not isinstance(cells, list) or not 1 <= len(cells) <= 64:
            raise ValueError('Invalid notebook cells')
        nodes = []; ids = set()
        for cell in cells:
            key, source, kind = cell['id'], cell['source'], cell['type']
            if key in ids or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', key) or len(source) > 100000:
                raise ValueError('Invalid or duplicate cell id')
            ids.add(key)
            if kind == 'markdown':
                node = nbformat.v4.new_markdown_cell(source, id=key)
            elif kind == 'code':
                node = nbformat.v4.new_code_cell(source, id=key)
                saved = self.cells.get(key)
                if saved and saved['source']==source and saved['result']['generation']==self.generation:
                    node.execution_count = saved['result']['execution_count']
                    for message in saved['result']['messages']:
                        typ, data = message['type'], message['content']
                        if typ == 'clear_output':
                            node.outputs.clear()
                        elif typ in ('stream', 'execute_result', 'display_data', 'error'):
                            allowed = {name: data[name] for name in {
                                'stream': ('name', 'text'), 'execute_result': ('data', 'metadata', 'execution_count'),
                                'display_data': ('data', 'metadata'), 'error': ('ename', 'evalue', 'traceback')
                            }[typ] if name in data}
                            node.outputs.append(nbformat.v4.new_output(typ, **allowed))
            else:
                raise ValueError('Code or Markdown cell required')
            nodes.append(node)
        notebook = nbformat.v4.new_notebook(cells=nodes)
        if self.selected:
            notebook.metadata.kernelspec = dict(name=self.selected,
                display_name=self.specs.get_kernel_spec(self.selected).display_name, language='python')
        nbformat.validate(notebook)
        nbformat.write(notebook, path)
        verified = nbformat.read(path, as_version=4); nbformat.validate(verified)
        return dict(path=str(path), cells=len(verified.cells), code_cells=sum(c.cell_type == 'code' for c in verified.cells))

    def dispatch(self, request):
        operation = request['operation']
        if operation == 'list': return dict(kernels=self.kernels())
        if operation == 'select': return self.select(request['name'])
        if operation == 'identity': return self.identity()
        if operation == 'restart': return self.restart()
        if operation == 'execute': return self.execute(request['cell_id'], request['code'])
        if operation == 'snapshot': return self.snapshot(request['expressions'])
        if operation == 'save': return self.save(request['filename'], request['cells'])
        if operation == 'stop': self.stop(); return dict(stopped=True)
        if operation == 'prepare':
            from guest_lessons import prepare
            return prepare(self, request['problem'])
        if operation == 'grade':
            from guest_lessons import grade
            return grade(self, request['problem'], request['baseline'], request['cells'])
        raise ValueError('Unknown notebook operation')


class Service(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True
    def __init__(self):
        self.notebook = Notebook()
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix='jupyter-client')
        self.lock = threading.Lock(); self.jobs = {}; self.current = None
        super().__init__(SOCKET, Handler)
        os.chmod(SOCKET, 0o600)

    def dispatch(self, request):
        action = request['action']
        if action == 'ping': return dict(ready=True, actual_jupyter=True)
        if action == 'interrupt': self.notebook.interrupt(); return dict(interrupted=True)
        if action == 'begin':
            with self.lock:
                if self.current and not self.current.done(): raise RuntimeError('이미 실행 중입니다.')
                self.jobs = {key: value for key, value in self.jobs.items() if not value.done()}
                key = uuid.uuid4().hex
                future = self.executor.submit(self.notebook.dispatch, request['request'])
                self.jobs[key] = self.current = future
            return dict(job=key)
        if action == 'poll':
            with self.lock: future = self.jobs[request['job']]
            # Future.result also raises TimeoutError when the task itself
            # failed with that exception. Do not turn that into endless polls.
            concurrent.futures.wait([future], timeout=.5)
            if not future.done(): return dict(done=False)
            result = future.result()
            return dict(done=True, result=result)
        raise ValueError('Unknown notebook service action')


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            line = self.rfile.readline(MAX_FRAME + 1)
            if len(line) > MAX_FRAME: raise ValueError('Notebook request too large')
            response = dict(ok=True, value=self.server.dispatch(json.loads(line)))
        except Exception as error:
            response = dict(ok=False, error=str(error)[-2500:])
        data = (json.dumps(response, ensure_ascii=False) + '\n').encode()
        if len(data) > MAX_FRAME:
            data = b'{"ok":false,"error":"Notebook response too large"}\n'
        self.wfile.write(data)


def client():
    request = sys.stdin.buffer.readline(MAX_FRAME + 1)
    if len(request) > MAX_FRAME: raise ValueError('Notebook request too large')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(4)
        connection.connect(SOCKET)
        connection.sendall(request.rstrip(b'\n') + b'\n')
        with connection.makefile('rb') as stream:
            reply = stream.readline(MAX_FRAME + 1)
        if len(reply) > MAX_FRAME: raise ValueError('Notebook response too large')
        sys.stdout.buffer.write(reply)


def main():
    if os.getuid() != 1100: raise RuntimeError('Notebook kernels must run as learner')
    if sys.argv[1] == 'client':
        client(); return
    sys.path.insert(0, '/opt/shellground')
    from agent import require_guest
    require_guest()
    path = Path(SOCKET)
    if path.exists():
        if not path.is_socket() or path.stat().st_uid != 1100: raise RuntimeError('Unexpected service socket owner')
        path.unlink()
    service = Service()
    def stopped(*_):
        service.notebook.interrupt()
        threading.Thread(target=service.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, stopped)
    try:
        service.serve_forever(poll_interval=.3)
    finally:
        service.executor.submit(service.notebook.stop).result(timeout=6)
        service.executor.shutdown(wait=False, cancel_futures=True)
        service.server_close(); path.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
