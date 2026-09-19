"""Run packaged-window checks with a window manager, as on a real desktop."""
import subprocess
import sys

manager = subprocess.Popen(['openbox', '--sm-disable'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    subprocess.run(sys.argv[1:], check=True, timeout=120)
finally:
    manager.terminate()
    try:
        manager.wait(timeout=5)
    except subprocess.TimeoutExpired:
        manager.kill(); manager.wait(timeout=5)
