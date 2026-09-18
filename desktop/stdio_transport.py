"""Restore inherited worker pipes in a frozen GUI executable, if absent."""
import os
import sys


def _restore_windows_descriptors(entries):
    """Bind inherited Win32 handles to CRT descriptors 0/1/2, not arbitrary fds.

    Capture duplicates BEFORE replacing any descriptor: stdout and stderr can
    name the same original Windows handle. Never transfer ownership of that
    original handle to msvcrt or close it ourselves.
    """
    import ctypes
    import msvcrt
    from windows_vm import system_dll
    kernel = system_dll('kernel32.dll')
    handle_type, dword = ctypes.c_void_p, ctypes.c_uint32
    kernel.GetStdHandle.argtypes = [dword]; kernel.GetStdHandle.restype = handle_type
    kernel.GetCurrentProcess.restype = handle_type
    kernel.DuplicateHandle.argtypes = [handle_type, handle_type, handle_type,
                                      ctypes.POINTER(handle_type), dword, ctypes.c_int32, dword]
    kernel.DuplicateHandle.restype = ctypes.c_int32
    kernel.CloseHandle.argtypes = [handle_type]; kernel.CloseHandle.restype = ctypes.c_int32
    duplicates = []
    try:
        process = kernel.GetCurrentProcess()
        for _, descriptor, mode in entries:
            original = kernel.GetStdHandle({0: -10, 1: -11, 2: -12}[descriptor])
            if not original or original == handle_type(-1).value:
                raise RuntimeError('Missing inherited worker pipe: ' + str(descriptor))
            duplicate = handle_type()
            if not kernel.DuplicateHandle(process, original, process, ctypes.byref(duplicate),
                                          0, False, 2):  # DUPLICATE_SAME_ACCESS
                raise OSError('Unable to duplicate inherited worker pipe')
            duplicates.append([descriptor, mode, duplicate.value])
        for entry in duplicates:
            descriptor, mode, handle = entry
            flags = (os.O_RDONLY if mode == 'r' else os.O_WRONLY) | os.O_BINARY
            fd = msvcrt.open_osfhandle(handle, flags)
            entry[2] = None  # ownership transferred to the CRT descriptor
            try:
                if fd != descriptor:
                    os.dup2(fd, descriptor, inheritable=False)
            finally:
                if fd != descriptor:
                    os.close(fd)
    finally:
        for _, _, handle in duplicates:
            if handle is not None: kernel.CloseHandle(handle)


def restore_worker_pipes():
    entries = [('stdin', 0, 'r'), ('stdout', 1, 'w'), ('stderr', 2, 'w')]
    missing = [entry for entry in entries if getattr(sys, entry[0]) is None]
    if missing and os.name == 'nt':
        _restore_windows_descriptors(missing)
    for name, descriptor, mode in missing:
        setattr(sys, name, open(descriptor, mode, encoding='utf-8', buffering=1, closefd=False))


def prepare_internal_stdio(flag):
    if sys.platform == 'win32' and (flag.startswith('--internal-') or flag.startswith('--self-test')):
        restore_worker_pipes()
