"""Actual CPython worker. Process separation is not an adversarial sandbox.

Only the learner's explicitly entered Python is executed. Ordinary file/network
mistakes are restricted; native extensions can bypass Python audit hooks. Do not
use this local backend to run downloaded or untrusted code.
"""
import ast
import base64
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import sys
import traceback


class CappedOutput(io.StringIO):
    def write(self, text):
        remaining = 65536 - self.tell()
        if remaining > 0: super().write(text[:remaining])
        return len(text)


def install_guardrails(workspace):
    root = Path(workspace).resolve()
    def within(path):
        if isinstance(path, int): return True
        try: return Path(os.fsdecode(path)).resolve().is_relative_to(root)
        except (ValueError, TypeError, OSError): return False
    def audit(event, args):
        if event.startswith(('subprocess.', 'socket.')) or event in ('os.system', 'os.exec', 'os.posix_spawn', 'os.fork', 'os.forkpty'):
            raise PermissionError('이 Python 실습에서는 외부 프로세스와 네트워크를 실행하지 않습니다.')
        if event == 'open':
            path, mode, flags = args
            writing = any(c in (mode or '') for c in 'wax+') or bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
            if writing and not within(path): raise PermissionError('실습 폴더 밖에는 저장할 수 없습니다.')
        if event in ('os.remove', 'os.rmdir', 'os.mkdir', 'os.chmod', 'os.chdir', 'os.truncate') and not within(args[0]):
            raise PermissionError('실습 폴더 밖은 변경할 수 없습니다.')
        if event in ('os.rename', 'os.link', 'os.symlink') and not all(within(p) for p in args[:2]):
            raise PermissionError('실습 폴더 밖의 파일은 연결하거나 이동할 수 없습니다.')
    sys.addaudithook(audit)


class Kernel:
    def __init__(self, workspace):
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as pd
        self.plt = plt
        self.workspace = Path(workspace).resolve()
        if str(self.workspace) not in sys.path: sys.path.insert(0,str(self.workspace))
        self.namespace = {'__name__': '__main__', '__builtins__': __builtins__}
        self.run_number = 0
        # Load fonts while writing remains possible inside the owned cache.
        from matplotlib import font_manager
        bundled_font = Path(__file__).resolve().parent.parent / 'assets/NotoSansCJK-Regular.ttc'
        if bundled_font.is_file():
            font_manager.fontManager.addfont(str(bundled_font))
            plt.rcParams['font.family'] = font_manager.FontProperties(fname=str(bundled_font)).get_name()
        plt.rcParams['axes.unicode_minus'] = False

    def execute(self, code):
        # A preceding cell can create a module within the same filesystem clock
        # tick (notably Android). Refresh directory discovery, not sys.modules.
        import importlib
        importlib.invalidate_caches()
        output = CappedOutput()
        error = None
        self.run_number += 1
        with redirect_stdout(output), redirect_stderr(output):
            try:
                tree = ast.parse(code, filename='<학습 셀>')
                expression = tree.body.pop() if tree.body and isinstance(tree.body[-1], ast.Expr) else None
                exec(compile(tree, '<학습 셀>', 'exec'), self.namespace)
                if expression:
                    value = eval(compile(ast.Expression(expression.value), '<학습 셀>', 'eval'), self.namespace)
                    if value is not None: print(repr(value)[:16000])
            except BaseException as exc:
                error = type(exc).__name__ + ': ' + str(exc)
                traceback.print_exception(type(exc), exc, exc.__traceback__, limit=5)
        return {'ok': error is None, 'error': error, 'output': output.getvalue(), 'execution': self.run_number}

    def inspect_values(self, names, probes=None):
        from .values import snapshot
        values, errors = {}, {}
        if probes:
            values['__probes__'] = {}
            with redirect_stdout(CappedOutput()), redirect_stderr(CappedOutput()):
                for name, cases in list(probes.items())[:10]:
                    try:
                        function = self.namespace[name]
                        if not callable(function): raise TypeError('함수가 아닙니다.')
                        values['__probes__'][name] = [snapshot(function(*args)) for args in cases[:10]]
                    except Exception as exc: errors[name] = str(exc)
        for name in names[:100]:
            if name.startswith('__memory__:'):
                import numpy as np
                try:
                    _,left,right=name.split(':')
                    values[name]=bool(np.shares_memory(self.namespace[left],self.namespace[right]))
                except (KeyError,TypeError,ValueError): pass
                continue
            if name.startswith('__generators__:'):
                import numpy as np
                try:
                    _,left,right=name.split(':')
                    a,b=self.namespace[left],self.namespace[right]
                    values[name]=isinstance(a,np.random.Generator) and isinstance(b,np.random.Generator) and a is not b
                except (KeyError,TypeError,ValueError): pass
                continue
            if name == '__files__':
                values[name] = self.file_snapshot()
                continue
            if name not in self.namespace: continue
            try: values[name] = snapshot(self.namespace[name])
            except Exception as exc: errors[name] = str(exc)
        return values,errors

    def inspect(self, names, probes=None):
        values,errors=self.inspect_values(names,probes)
        figures,figure_numbers,preview_errors = [],[],[]
        numbers = self.plt.get_fignums()
        if numbers:
            # Prefer the current Figure, not the first (possibly empty) figure
            # from an earlier execution. Inspecting an empty session must not
            # create a figure as a side effect.
            active = self.plt.gcf()
            ordered = [active.number] + [n for n in reversed(numbers) if n != active.number]
            try:
                for number in ordered[:6]:
                    try:
                        fig = self.plt.figure(number)
                        stream = io.BytesIO()
                        # Bound preview pixels without changing the learner's
                        # physical size or semantic grading. Isolate failures.
                        preview_dpi=min(90,1600/max(fig.get_size_inches()))
                        fig.savefig(stream, format='png', dpi=preview_dpi)
                        if stream.tell() > 4 * 1024 * 1024:
                            raise ValueError('그래프 미리보기 크기 제한(4 MiB)을 넘었습니다.')
                        figures.append(base64.b64encode(stream.getvalue()).decode())
                        figure_numbers.append(number)
                    except Exception as exc:
                        preview_errors.append({'number':number,'error':str(exc)[:1000]})
            finally:
                # Do not redirect the next plt.plot/savefig call to a different
                # Figure simply because we rendered previews for the UI.
                self.plt.figure(active.number)
        return {'ok': True, 'values': values, 'inspection_errors': errors, 'figures': figures,
                'figure_numbers':figure_numbers, 'preview_errors':preview_errors,
                'figure_count':len(numbers)}

    def file_snapshot(self):
        """Bounded inspection of output artifacts, independent of learner variables."""
        from itertools import islice
        files = {}
        for path in islice(self.workspace.rglob('*'), 400):
            relative = path.relative_to(self.workspace)
            if any(part.startswith('.') for part in relative.parts) or path.is_symlink() or not path.is_file(): continue
            if not path.resolve().is_relative_to(self.workspace): continue
            with path.open('rb') as stream: data = stream.read(65536)
            item = {'size':path.stat().st_size, 'kind':'binary'}
            if data.startswith(b'\x89PNG\r\n\x1a\n'):
                from PIL import Image
                try:
                    with Image.open(path) as img:
                        img.verify()
                    with Image.open(path) as img:
                        item.update(kind='png', width=img.width, height=img.height)
                        item['matches_fig']=self.png_matches_figure(img)
                except (OSError, ValueError): item['kind'] = 'invalid-image'
            else:
                try:
                    item.update(kind='text', text=data.decode('utf-8'))
                    if b'<svg' in data:
                        import xml.etree.ElementTree as ET
                        try:
                            tree=ET.fromstring(data)
                            if tree.tag=='{http://www.w3.org/2000/svg}svg':
                                item['kind']='svg'
                                item['has_paths']=bool(tree.findall('.//{http://www.w3.org/2000/svg}path'))
                                item['matches_fig']=self.svg_matches_figure(tree)
                        except ET.ParseError: item['kind']='invalid-svg'
                except UnicodeDecodeError: pass
            files[relative.as_posix()] = item
        return files

    def png_matches_figure(self,image):
        from matplotlib.figure import Figure
        from PIL import Image
        figure=self.namespace.get('fig')
        if not isinstance(figure,Figure): return False
        dpi=image.width/figure.get_size_inches()[0]
        if abs(image.height-figure.get_size_inches()[1]*dpi)>1: return False
        stream=io.BytesIO()
        figure.savefig(stream,format='png',dpi=dpi)
        stream.seek(0)
        with Image.open(stream) as expected:
            return image.size==expected.size and image.convert('RGBA').tobytes()==expected.convert('RGBA').tobytes()

    def svg_matches_figure(self,actual):
        import xml.etree.ElementTree as ET
        from matplotlib.figure import Figure
        figure=self.namespace.get('fig')
        if not isinstance(figure,Figure): return False
        stream=io.BytesIO(); figure.savefig(stream,format='svg')
        expected=ET.fromstring(stream.getvalue())
        def geometry(tree):
            return sorted((' '.join(p.attrib.get('d','').split()),p.attrib.get('style',''))
                          for p in tree.findall('.//{http://www.w3.org/2000/svg}path'))
        return actual.attrib.get('viewBox')==expected.attrib.get('viewBox') and geometry(actual)==geometry(expected)


def main(workspace):
    root = Path(workspace).resolve()
    if not root.is_dir() or not (root / '.shellground-python-session').is_file():
        raise RuntimeError('앱 소유 실습 폴더가 아닙니다.')
    os.chdir(root)
    os.environ['MPLCONFIGDIR'] = str(root / '.mpl-cache')
    os.environ['XDG_CACHE_HOME'] = str(root / '.cache')
    if hasattr(os, 'nice'): os.nice(10)
    if sys.platform == 'linux':
        import resource
        resource.setrlimit(resource.RLIMIT_FSIZE, (32 * 1024 * 1024, 32 * 1024 * 1024))
        # Prevent one learner array allocation from exhausting a laptop.
        resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
    kernel = Kernel(root)
    install_guardrails(root)
    protocol = sys.stdout
    def send(value):
        protocol.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + '\n')
        protocol.flush()
    send({'ready': True})
    for line in sys.stdin:
        try:
            request = json.loads(line)
            if request['action'] == 'close': break
            if request['action'] == 'execute': result = kernel.execute(request.get('code', ''))
            elif request['action'] == 'inspect': result = kernel.inspect(request.get('names', []), request.get('probes'))
            else: raise ValueError('알 수 없는 Python 요청')
            send(result)
        except Exception as exc:
            send({'ok': False, 'error': str(exc), 'output': ''})
    return 0
