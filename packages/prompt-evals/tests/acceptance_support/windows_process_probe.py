import ctypes
import sys
from typing import Final

SYNCHRONIZE_ACCESS: Final[int] = 0x00100000
HANDLE_NOT_INHERITED: Final[int] = 0
WAIT_OBJECT_0: Final[int] = 0
MILLISECONDS_PER_SECOND: Final[int] = 1000


class WindowsProcessProbe:
    """Tells a test whether a Windows process, found by its id, has ended."""

    @staticmethod
    def has_process_ended_within(process_id: int, timeout_seconds: float) -> bool:
        kernel32: ctypes.WinDLL = WindowsProcessProbe._load_kernel32()
        process_handle: int | None = kernel32.OpenProcess(SYNCHRONIZE_ACCESS, HANDLE_NOT_INHERITED, process_id)
        # Windows refuses to open a process id that no longer exists.
        if not process_handle:
            return True
        try:
            return kernel32.WaitForSingleObject(process_handle, round(timeout_seconds * MILLISECONDS_PER_SECOND)) == WAIT_OBJECT_0
        finally:
            kernel32.CloseHandle(process_handle)

    @staticmethod
    def _load_kernel32() -> ctypes.WinDLL:
        if sys.platform != "win32":
            raise NotImplementedError("WindowsProcessProbe runs only on Windows.")
        kernel32: ctypes.WinDLL = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = (ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32)
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.WaitForSingleObject.argtypes = (ctypes.c_void_p, ctypes.c_uint32)
        kernel32.WaitForSingleObject.restype = ctypes.c_uint32
        kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
        kernel32.CloseHandle.restype = ctypes.c_int
        return kernel32
