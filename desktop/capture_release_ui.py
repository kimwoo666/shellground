"""Capture the actual native widgets using an isolated, disposable profile."""
import os
from pathlib import Path
import tempfile
import time
import argparse


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--terminal-only',action='store_true');args=parser.parse_args()
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    from native_app import create_application
    from study_window import StudyWindow
    app,ui,mono=create_application()
    target=Path(__file__).resolve().parents[1]/'docs/screenshots'
    target.mkdir(parents=True,exist_ok=True)
    def wait(predicate):
        deadline=time.monotonic()+120
        while not predicate() and time.monotonic()<deadline:
            app.processEvents();time.sleep(.02)
        if not predicate():raise RuntimeError('Screenshot example did not finish')
    with tempfile.TemporaryDirectory(prefix='shellground-readme-') as profile:
        window=StudyWindow(ui,mono,Path(profile)/'progress.json',mode='real')
        window.resize(1400,960);window.show();app.processEvents()
        try:
            if args.terminal_only:
                linux=window.pages['linux']
                linux.engine.root=Path(__file__).resolve().parent/'dist-linux-4.7.4-review/runtime/linux-x86_64'
                linux.try_lesson();wait(lambda:not linux.busy and linux.terminal.connected)
                linux.engine.send(b'pwd\nls -al ~\n')
                wait(lambda:'total ' in '\n'.join(linux.terminal.screen.display))
                window.grab().save(str(target/'linux-learning.png'))
                print('Captured actual guest terminal; no course replay',flush=True)
                return
            window.grab().save(str(target/'linux-learning.png'))
            window.switch_mode('python');app.processEvents();page=window.pages['python']
            page.index=next(i for i,u in enumerate(page.units) if u.topic=='Matplotlib')
            page.phase='example';page.variant=0;page.render()
            # A real, smaller Figure fits this capture's native plot viewport.
            # It is executed and graded normally, never painted into a mock UI.
            page.editor.setPlainText(page.problem.solution.replace('plt.subplots()','plt.subplots(figsize=(4.3, 2.8))'))
            page.run_code();wait(lambda:not page.busy)
            window.grab().save(str(target/'python-plot.png'))
            page.grade();wait(lambda:not page.busy)
            if not page.solved:raise RuntimeError('Screenshot example grading failed')
            window.grab().save(str(target/'python-grading.png'))
            print('Captured actual Linux Qt UI and one Matplotlib example; no full course replay',flush=True)
        finally:
            window.close();wait(lambda:window._shutdown_ready)


if __name__=='__main__':main()
