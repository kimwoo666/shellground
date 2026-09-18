"""Native Windows GUI pipe/Job probe; no old curriculum or VM is launched."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time

PAYLOAD = '한글 경로, 공백 · EOF 연결 확인\n'
ERROR_MARKER = '감독 프로세스 오류 통로 확인\n'


def require_native():
    if sys.platform != 'win32' or not getattr(sys, 'frozen', False):
        raise RuntimeError('Requires the actual frozen Windows executable; source/Linux is not native proof')


def query_job(kernel, handle, kind, structure):
    kernel.QueryInformationJobObject.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                                ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p]
    kernel.QueryInformationJobObject.restype = ctypes.c_int32
    value = structure()
    if not kernel.QueryInformationJobObject(handle, kind, ctypes.byref(value), ctypes.sizeof(value), None):
        raise OSError('Cannot query actual Windows Job limits')
    return value


def probe():
    require_native()
    from windows_vm import create_guard_job, system_dll, CpuLimits, ExtendedLimits
    # This diagnostic child, not the UI/test parent, receives the CPU budget.
    handle = create_guard_job()
    kernel = system_dll('kernel32.dll')
    cpu = query_job(kernel, handle, 15, CpuLimits)
    life = query_job(kernel, handle, 9, ExtendedLimits)
    kernel.GetActiveProcessorCount.argtypes = [ctypes.c_uint16]
    kernel.GetActiveProcessorCount.restype = ctypes.c_uint32
    logical_cpus = kernel.GetActiveProcessorCount(0xffff)
    data = bytearray()
    while True:
        block = os.read(0, 1024)  # specifically exercise descriptor 0 / parent EOF
        if not block: break
        data.extend(block)
        if len(data) > 8192: raise ValueError('Probe input is too large')
    # Bounded 3s of actual work under the new job, not an uncapped benchmark.
    started, used = time.monotonic(), time.process_time()
    iterations = 0
    while time.monotonic() - started < 3:
        sum(range(500))
        iterations += 1
    wall, consumed = time.monotonic() - started, time.process_time() - used
    result = dict(echo=data.decode('utf-8'), eof=True, cpu_flags=cpu.flags, cpu_rate=cpu.rate,
                  logical_cpus=logical_cpus, utf8_mode=sys.flags.utf8_mode,
                  kill_on_close=bool(life.basic.flags & 0x2000),
                  cpu_seconds=consumed, wall_seconds=wall, iterations=iterations)
    os.write(2, ERROR_MARKER.encode('utf-8'))
    print(json.dumps(result, ensure_ascii=False), flush=True)  # restored sys.stdout
    return 0  # handle is intentionally held until OS process teardown


def validate_probe(completed):
    if completed.returncode != 0: raise RuntimeError('Native pipe probe failed: ' + completed.stderr[-2000:])
    if completed.stderr != ERROR_MARKER: raise RuntimeError('Native raw stderr descriptor changed')
    value = json.loads(completed.stdout)
    if value.get('echo') != PAYLOAD or value.get('eof') is not True:
        raise RuntimeError('Native Unicode input/EOF contract failed')
    if value.get('utf8_mode') != 1: raise RuntimeError('Native interpreter UTF-8 mode is not enabled')
    from windows_vm import cpu_rate
    try: expected_rate = cpu_rate(value.get('logical_cpus'))
    except ValueError as error: raise RuntimeError('Native CPU count is missing') from error
    if value.get('cpu_flags') != 5 or value.get('cpu_rate') != expected_rate or value.get('kill_on_close') is not True:
        raise RuntimeError('Native Job policy not applied')
    if value.get('iterations', 0) <= 0 or not 3 <= value.get('wall_seconds', 0) <= 15:
        raise RuntimeError('Native CPU observation did not run in a bounded interval')
    # Scheduling intervals and accounting granularity need a small tolerance.
    # This proves this diagnostic child's cap, not WHPX guest CPU accounting.
    if not 0 <= value.get('cpu_seconds', -1) <= value['wall_seconds'] * .6 + .2:
        raise RuntimeError('Observed child CPU time exceeded the conservative budget')
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args(argv)
    require_native()
    if args.report.exists(): raise FileExistsError('Preserve earlier native evidence')
    report = dict(kind='native-windows-pipe-job-probe', platform=sys.platform, frozen=True,
                  state='in_progress', full_course_rerun=False, vm_tested=False)
    try:
        from vm_resources import vm_process_options
        result = subprocess.run([sys.executable, '--internal-windows-pipe-probe'], input=PAYLOAD,
                                text=True, encoding='utf-8', capture_output=True, timeout=45,
                                env=dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT='1'), **vm_process_options())
        report.update(state='complete', observed=validate_probe(result))
    except BaseException as error:
        report.update(state='failed', error=str(error)); raise
    finally:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2); stream.write('\n')
        print(json.dumps(report, ensure_ascii=False), flush=True)
    return 0


if __name__ == '__main__': raise SystemExit(main())
