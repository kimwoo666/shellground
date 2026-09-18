"""Conservative VM defaults; Windows software execution requires a CPU cap."""
import os
import sys

from engine import LabError


def available_cpus():
    try:
        return max(1, len(os.sched_getaffinity(0)))
    except (AttributeError, OSError):
        return max(1, os.cpu_count() or 1)


def vcpu_count(host_cpus=None):
    # Leave at least half the scheduling capacity for the desktop. vCPUs are
    # independent guest processors, not CPU affinity or a host usage quota.
    count = available_cpus() if host_cpus is None else max(1, host_cpus)
    return max(1, min(4, count // 2))


def kvm_usable():
    if sys.platform != 'linux':
        return False
    try:
        import fcntl
        # Opening the device and querying its API catches permission/sandbox
        # failures that checking existence alone cannot detect.
        with open('/dev/kvm', 'rb+', buffering=0) as device:
            return fcntl.ioctl(device, 0xAE00, 0) == 12  # KVM_GET_API_VERSION
    except (OSError, ImportError):
        return False


def accelerator_args(allow_software=False):
    if sys.platform == 'linux' and kvm_usable():
        return ['-accel', 'kvm', '-cpu', 'host']
    if sys.platform == 'win32':
        from windows_vm import accelerator_args as windows_accelerator_args
        return windows_accelerator_args()
    if allow_software:
        return ['-accel', 'tcg,thread=multi', '-cpu', 'max']
    raise LabError('하드웨어 가속을 사용할 수 없습니다. 노트북의 지속적인 고부하를 막기 위해 '
                   '소프트웨어 에뮬레이션으로 자동 전환하지 않습니다. '
                   '현재 실행 환경의 가속 장치 접근을 확인하거나 시뮬레이션 모드를 사용하세요.')


def lower_priority(process):
    """Favor host interaction under contention, not a promised CPU/heat cap."""
    if os.name == 'posix':
        try:
            os.setpriority(os.PRIO_PROCESS, process.pid, 10)
            if sys.platform == 'linux':
                # Linux nice values are per-thread. Include vCPU threads that
                # were already created before the parent adjusted priority.
                from pathlib import Path
                for task in (Path('/proc') / str(process.pid) / 'task').iterdir():
                    try:
                        os.setpriority(os.PRIO_PROCESS, int(task.name), 10)
                    except (OSError, ValueError):
                        pass
        except (OSError, AttributeError):
            pass


def vm_process_options():
    if os.name == 'nt':
        import subprocess
        return {'creationflags': subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS}
    return {}
