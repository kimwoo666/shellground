"""Native, self-contained setup window. The learning app is not rebuilt."""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import hashlib
import urllib.request
import tkinter as tk
from tkinter import ttk, messagebox
from core import Setup, Cancelled, register_launcher

ASSETS = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))


def main():
    root = tk.Tk()
    root.title('Shellground 설치')
    root.geometry('610x365')
    root.minsize(560, 340)
    root.configure(background='#f4f6f8')
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('TFrame', background='#f4f6f8')
    style.configure('TLabel', background='#f4f6f8', foreground='#182230', font=('sans-serif', 11))
    style.configure('Title.TLabel', font=('sans-serif', 23, 'bold'))
    style.configure('TButton', padding=(16, 10), font=('sans-serif', 11))
    panel = ttk.Frame(root, padding=28)
    panel.pack(fill='both', expand=True)
    ttk.Label(panel, text='Shellground', style='Title.TLabel').pack(anchor='w')
    ttk.Label(panel, text='Linux · Docker · ROS 2 · Python', foreground='#487366').pack(anchor='w', pady=(3, 20))
    ttk.Label(panel, text='설치를 누르면 필요한 자료를 자동으로 준비합니다.\n첫 설치: 인터넷 연결 · 약 8.1GB 다운로드 · 9GB 여유 공간\n설치 후에는 앱 메뉴에서 Shellground를 실행하세요.', justify='left').pack(anchor='w')
    status = tk.StringVar(value='설치 준비 완료')
    ttk.Label(panel, textvariable=status).pack(anchor='w', pady=(20, 8))
    bar = ttk.Progressbar(panel, maximum=100)
    bar.pack(fill='x')
    actions = ttk.Frame(panel)
    actions.pack(fill='x', side='bottom', pady=(18, 0))
    cancel = threading.Event()
    messages = queue.Queue(maxsize=8)
    running = [False]
    application = [None]
    last_update = [0.0]
    data_root = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
    destination = data_root / 'shellground-app'

    def progress(label, current, total):
        now = time.monotonic()
        if now - last_update[0] < .2 and current != total:
            return
        last_update[0] = now
        try: messages.put_nowait(('progress', label, current, total))
        except queue.Full: pass

    def install():
        try:
            manifest = json.loads((ASSETS / 'manifest.json').read_text())
            app = Setup(destination, manifest, progress, cancel).install()
            register_launcher(app, ASSETS / 'shellground.svg', data_root)
            messages.put(('done', app))
        except Exception as error:
            messages.put(('error', str(error)))

    def start():
        if application[0]:
            environment = dict(os.environ)
            # Do not leak the installer's extracted Tcl/Python library paths
            # into the separately packaged learning application.
            for name in ('TCL_LIBRARY', 'TK_LIBRARY', 'PYTHONHOME', 'PYTHONPATH'):
                environment.pop(name, None)
            if 'LD_LIBRARY_PATH_ORIG' in environment:
                environment['LD_LIBRARY_PATH'] = environment.pop('LD_LIBRARY_PATH_ORIG')
            else: environment.pop('LD_LIBRARY_PATH', None)
            environment['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
            try:
                subprocess.Popen([str(application[0] / 'Shellground')], cwd=application[0],
                    env=environment, start_new_session=True)
            except OSError as error:
                messagebox.showerror('Shellground 실행', str(error))
                return
            root.destroy()
            return
        running[0] = True
        cancel.clear()
        primary.configure(state='disabled')
        secondary.configure(text='취소')
        status.set('설치 시작 중…')
        threading.Thread(target=install, daemon=False).start()

    def close():
        if running[0]:
            cancel.set()
            status.set('중단 중… 확인된 자료는 다음 설치에서 이어 받습니다.')
        else: root.destroy()

    secondary = ttk.Button(actions, text='닫기', command=close)
    secondary.pack(side='right')
    primary = ttk.Button(actions, text='설치', command=start)
    primary.pack(side='right', padx=10)
    root.protocol('WM_DELETE_WINDOW', close)

    def poll():
        try:
            while True:
                item = messages.get_nowait()
                if item[0] == 'progress':
                    _, label, current, total = item
                    status.set(label + (f' · {current/1e9:.2f} / {total/1e9:.2f} GB' if total else ''))
                    bar['value'] = 100 * current / total if total else 0
                else:
                    running[0] = False
                    primary.configure(state='normal')
                    secondary.configure(text='닫기')
                    if item[0] == 'done':
                        application[0] = item[1]
                        status.set('설치 완료 · 앱 메뉴에 Shellground가 추가됐습니다.')
                        bar['value'] = 100
                        primary.configure(text='Shellground 실행')
                    else:
                        status.set(item[1][:110])
                        primary.configure(text='다시 시도')
        except queue.Empty: pass
        root.after(100, poll)
    root.after(100, poll)
    if '--smoke-ui' in sys.argv:
        root.after(700, root.destroy)
    root.mainloop()


if __name__ == '__main__':
    if '--check-network' in sys.argv:
        with urllib.request.urlopen('https://github.com/kimwoo666/shellground/releases/download/v4.7.4-preview/pc-build.json', timeout=20) as response:
            data = response.read(16384)
        if hashlib.sha256(data).hexdigest() != 'dd0634bc13c1215e97a8395c2de738d698459c415192dd9a0f9cabec0e42c63c':
            raise ValueError('Release identity check failed')
        print('HTTPS + release checksum: PASS (1.6 KB only)')
    else:
        main()
