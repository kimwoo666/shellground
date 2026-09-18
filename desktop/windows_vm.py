"""Windows-only VM policy. No feature installation, elevation or host shell.

QEMU and its supervisor share one CPU-limited, kill-on-close Job Object.
The UI stays outside that job. This is a CPU scheduling budget, not a
temperature guarantee; real Windows validation is required before release.
"""
import ctypes


# Explicit Windows ABI widths also allow contract tests on a Linux builder.
DWORD = ctypes.c_uint32
HANDLE = ctypes.c_void_p


class BasicLimits(ctypes.Structure):
    _fields_ = [('process_time', ctypes.c_int64), ('job_time', ctypes.c_int64),
                ('flags', DWORD), ('min_ws', ctypes.c_size_t), ('max_ws', ctypes.c_size_t),
                ('active', DWORD), ('affinity', ctypes.c_size_t),
                ('priority', DWORD), ('scheduling', DWORD)]


class ExtendedLimits(ctypes.Structure):
    _fields_ = [('basic', BasicLimits), ('io', ctypes.c_uint64 * 6),
                ('process_memory', ctypes.c_size_t), ('job_memory', ctypes.c_size_t),
                ('peak_process_memory', ctypes.c_size_t), ('peak_job_memory', ctypes.c_size_t)]


class CpuLimits(ctypes.Structure):
    _fields_ = [('flags', DWORD), ('rate', DWORD)]


def system_dll(name):
    # Never load a similarly named DLL from the current working directory.
    return ctypes.WinDLL(name, use_last_error=True, winmode=0x800)


def hypervisor_present():
    """Read capability only. A positive result isn't proof QEMU can start."""
    try:
        function = system_dll('WinHvPlatform.dll').WHvGetCapability
        function.argtypes = [ctypes.c_int32, ctypes.c_void_p, DWORD, ctypes.POINTER(DWORD)]
        function.restype = ctypes.c_int32  # HRESULT is 32 bits, including on x64
        value, written = ctypes.c_uint64(), DWORD()
        result = function(0, ctypes.byref(value), ctypes.sizeof(value), ctypes.byref(written))
        return result == 0 and written.value >= 4 and bool(value.value & 0xffffffff)
    except (OSError, AttributeError):
        return False


def cpu_rate(host_cpus):
    """<= 0.6 logical CPU in total, NOT 60% of the entire computer.

    Windows uses 1..10000 units of total CPU capacity. Nested job limits can
    reduce this further. Never pin work to a single core.
    """
    if type(host_cpus) is not int or not 1 <= host_cpus <= 1024:
        raise ValueError('Invalid logical CPU count')
    return max(1, 6000 // host_cpus)


def _error():
    return ctypes.WinError(ctypes.get_last_error())


def create_guard_job(kernel=None, host_cpus=None):
    """Called inside the fresh supervisor before spawning any QEMU thread.

    Failure to apply either limit aborts startup. The non-inheritable handle
    must remain open until supervisor teardown, so a crash kills children.
    """
    kernel = kernel if kernel is not None else system_dll('kernel32.dll')
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
    kernel.CreateJobObjectW.restype = HANDLE
    kernel.SetInformationJobObject.argtypes = [HANDLE, ctypes.c_int, ctypes.c_void_p, DWORD]
    kernel.SetInformationJobObject.restype = ctypes.c_int32
    kernel.AssignProcessToJobObject.argtypes = [HANDLE, HANDLE]
    kernel.AssignProcessToJobObject.restype = ctypes.c_int32
    kernel.GetCurrentProcess.restype = HANDLE
    kernel.CloseHandle.argtypes = [HANDLE]
    kernel.CloseHandle.restype = ctypes.c_int32
    if host_cpus is None:
        kernel.GetActiveProcessorCount.argtypes = [ctypes.c_uint16]
        kernel.GetActiveProcessorCount.restype = DWORD
        host_cpus = kernel.GetActiveProcessorCount(0xffff)  # ALL_PROCESSOR_GROUPS
    rate = cpu_rate(host_cpus)  # fail closed on an invalid OS response
    handle = kernel.CreateJobObjectW(None, None)
    if not handle:
        raise _error()
    try:
        lifetime = ExtendedLimits()
        lifetime.basic.flags = 0x2000  # KILL_ON_JOB_CLOSE
        cpu = CpuLimits(0x1 | 0x4, rate)  # ENABLE | HARD_CAP
        for info_class, value in ((9, lifetime), (15, cpu)):
            if not kernel.SetInformationJobObject(handle, info_class, ctypes.byref(value), ctypes.sizeof(value)):
                raise _error()
        if not kernel.AssignProcessToJobObject(handle, kernel.GetCurrentProcess()):
            raise _error()
    except BaseException:
        kernel.CloseHandle(handle)
        raise
    return handle


def accelerator_args():
    # Choose once and report it. Do not retry an arbitrary failed WHPX boot
    # under TCG: broken images/permissions must not turn into hidden retries.
    if hypervisor_present():
        return ['-accel', 'whpx', '-cpu', 'max']
    return ['-accel', 'tcg,thread=multi', '-cpu', 'max']


def boot_timeout(acceleration):
    # Software translation with a hard cap is slower. Still cancellable in
    # RealEngine's normal one-second loop, never a long blocking sleep.
    return 600 if acceleration[1].startswith('tcg') else 120


def startup_description(acceleration, cpus):
    method = '하드웨어 가속 WHPX' if acceleration[1] == 'whpx' else '소프트웨어 실행 TCG (시작이 느릴 수 있음)'
    return f'{method} · 가상 CPU {cpus}개 · 메모리 2 GiB · VM CPU 예산: 논리 코어 0.6개분'


def option_path(path):
    """QEMU option-list escaping, separate from subprocess argv quoting."""
    return str(path).replace('\\', '/').replace(',', ',,')


def supervisor_output():
    # The supervisor must be able to delete qemu.log before the UI closes its
    # own output handle. Windows refuses that unlink for an ordinary open file.
    import tempfile
    return tempfile.TemporaryFile(mode='w+b')


def forward_qemu_error(path):
    """Retain a bounded diagnostic before the supervisor removes its session."""
    import os
    with path.open('rb') as stream:
        stream.seek(0, os.SEEK_END)
        stream.seek(max(0, stream.tell() - 3000))
        message = stream.read(3000)
    if message:
        os.write(2, message)
