import ctypes
import errno
import sys
from typing import Final, final

# CreateProcess flag: the primary thread starts suspended, so the process runs no code until it is resumed.
CREATE_SUSPENDED: Final[int] = 0x00000004
TOOLHELP_SNAPSHOT_THREADS: Final[int] = 0x00000004
ALL_PROCESSES: Final[int] = 0
THREAD_SUSPEND_RESUME: Final[int] = 0x0002
THREAD_HANDLE_NOT_INHERITED: Final[int] = 0
RESUME_THREAD_FAILED: Final[int] = 0xFFFFFFFF
NO_MORE_FILES_ERROR_CODE: Final[int] = 18
INVALID_HANDLE_VALUE: Final[int | None] = ctypes.c_void_p(-1).value


class _ThreadEntry32(ctypes.Structure):
    _fields_ = (
        ("dwSize", ctypes.c_uint32),
        ("cntUsage", ctypes.c_uint32),
        ("th32ThreadID", ctypes.c_uint32),
        ("th32OwnerProcessID", ctypes.c_uint32),
        ("tpBasePri", ctypes.c_int32),
        ("tpDeltaPri", ctypes.c_int32),
        ("dwFlags", ctypes.c_uint32),
    )


@final
class WindowsSuspendedProcess:
    """Resumes a process created with CREATE_SUSPENDED.

    subprocess closes the primary thread handle CreateProcess returned, so the process's threads are found again
    through a Toolhelp snapshot; a process created suspended has only its primary thread.
    """

    @staticmethod
    def resume(process_id: int) -> None:
        kernel32: ctypes.WinDLL = WindowsSuspendedProcess._load_kernel32()
        thread_ids: tuple[int, ...] = WindowsSuspendedProcess._find_thread_ids(kernel32, process_id)
        if not thread_ids:
            raise ProcessLookupError(errno.ESRCH, f"Process {process_id} has no thread to resume")
        for thread_id in thread_ids:
            WindowsSuspendedProcess._resume_thread(kernel32, thread_id)

    @staticmethod
    def _find_thread_ids(kernel32: ctypes.WinDLL, process_id: int) -> tuple[int, ...]:
        snapshot_handle: int | None = kernel32.CreateToolhelp32Snapshot(TOOLHELP_SNAPSHOT_THREADS, ALL_PROCESSES)
        if snapshot_handle is None or snapshot_handle == INVALID_HANDLE_VALUE:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            return WindowsSuspendedProcess._read_thread_ids(kernel32, snapshot_handle, process_id)
        finally:
            kernel32.CloseHandle(snapshot_handle)

    @staticmethod
    def _read_thread_ids(kernel32: ctypes.WinDLL, snapshot_handle: int, process_id: int) -> tuple[int, ...]:
        thread_entry: _ThreadEntry32 = _ThreadEntry32()
        thread_entry.dwSize = ctypes.sizeof(_ThreadEntry32)
        thread_ids: list[int] = []
        has_thread_entry: bool = bool(kernel32.Thread32First(snapshot_handle, ctypes.byref(thread_entry)))
        while has_thread_entry:
            if thread_entry.th32OwnerProcessID == process_id:
                thread_ids.append(thread_entry.th32ThreadID)
            has_thread_entry = bool(kernel32.Thread32Next(snapshot_handle, ctypes.byref(thread_entry)))
        last_error_code: int = ctypes.get_last_error()
        # The walk ends with "no more files"; any other error means the snapshot could not be read to its end.
        if last_error_code != NO_MORE_FILES_ERROR_CODE:
            raise ctypes.WinError(last_error_code)
        return tuple(thread_ids)

    @staticmethod
    def _resume_thread(kernel32: ctypes.WinDLL, thread_id: int) -> None:
        thread_handle: int | None = kernel32.OpenThread(THREAD_SUSPEND_RESUME, THREAD_HANDLE_NOT_INHERITED, thread_id)
        if not thread_handle:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if kernel32.ResumeThread(thread_handle) == RESUME_THREAD_FAILED:
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            kernel32.CloseHandle(thread_handle)

    @staticmethod
    def _load_kernel32() -> ctypes.WinDLL:
        if sys.platform != "win32":
            raise NotImplementedError("Suspended process creation exists only on Windows.")
        kernel32: ctypes.WinDLL = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateToolhelp32Snapshot.argtypes = (ctypes.c_uint32, ctypes.c_uint32)
        kernel32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
        kernel32.Thread32First.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
        kernel32.Thread32First.restype = ctypes.c_int
        kernel32.Thread32Next.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
        kernel32.Thread32Next.restype = ctypes.c_int
        kernel32.OpenThread.argtypes = (ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32)
        kernel32.OpenThread.restype = ctypes.c_void_p
        kernel32.ResumeThread.argtypes = (ctypes.c_void_p,)
        kernel32.ResumeThread.restype = ctypes.c_uint32
        kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
        kernel32.CloseHandle.restype = ctypes.c_int
        return kernel32
