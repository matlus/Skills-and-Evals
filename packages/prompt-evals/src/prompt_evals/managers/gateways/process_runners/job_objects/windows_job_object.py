import ctypes
import sys
from typing import Final, final

JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE: Final[int] = 0x2000
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS: Final[int] = 9
PROCESS_SET_QUOTA: Final[int] = 0x0100
PROCESS_TERMINATE: Final[int] = 0x0001
TERMINATED_PROCESS_EXIT_CODE: Final[int] = 1
PROCESS_HANDLE_NOT_INHERITED: Final[int] = 0


class _JobObjectBasicLimitInformation(ctypes.Structure):
    _fields_ = (
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", ctypes.c_uint32),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", ctypes.c_uint32),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", ctypes.c_uint32),
        ("SchedulingClass", ctypes.c_uint32),
    )


class _IoCounters(ctypes.Structure):
    _fields_ = (
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    )


class _JobObjectExtendedLimitInformation(ctypes.Structure):
    _fields_ = (
        ("BasicLimitInformation", _JobObjectBasicLimitInformation),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    )


@final
class WindowsJobObject:
    """A Windows Job Object holding one process and every process it starts.

    Job membership is inherited by every descendant, so terminating or closing the job also ends a tool command whose
    parent already exited, which a PID-rooted `taskkill /T` walk can no longer reach.
    """

    def __init__(self, kernel32: ctypes.WinDLL, job_handle: int) -> None:
        self._kernel32: Final[ctypes.WinDLL] = kernel32
        self._job_handle: Final[int] = job_handle

    @staticmethod
    def contain_process(process_id: int) -> WindowsJobObject:
        kernel32: ctypes.WinDLL = WindowsJobObject._load_kernel32()
        windows_job_object: WindowsJobObject = WindowsJobObject(kernel32, WindowsJobObject._create_job_handle(kernel32))
        try:
            windows_job_object._end_processes_when_closed()
            windows_job_object._assign_process(process_id)
        except BaseException:
            windows_job_object.close()
            raise
        return windows_job_object

    @staticmethod
    def _create_job_handle(kernel32: ctypes.WinDLL) -> int:
        job_handle: int | None = kernel32.CreateJobObjectW(None, None)
        if not job_handle:
            raise ctypes.WinError(ctypes.get_last_error())
        return job_handle

    def terminate(self) -> None:
        if not self._kernel32.TerminateJobObject(self._job_handle, TERMINATED_PROCESS_EXIT_CODE):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self) -> None:
        # With kill-on-close set, closing the last handle also ends any process still in the job.
        self._kernel32.CloseHandle(self._job_handle)

    def _end_processes_when_closed(self) -> None:
        job_object_extended_limit_information: _JobObjectExtendedLimitInformation = _JobObjectExtendedLimitInformation()
        job_object_extended_limit_information.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self._kernel32.SetInformationJobObject(
            self._job_handle,
            JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
            ctypes.byref(job_object_extended_limit_information),
            ctypes.sizeof(job_object_extended_limit_information),
        ):
            raise ctypes.WinError(ctypes.get_last_error())

    def _assign_process(self, process_id: int) -> None:
        process_handle: int | None = self._kernel32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE, PROCESS_HANDLE_NOT_INHERITED, process_id)
        if not process_handle:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if not self._kernel32.AssignProcessToJobObject(self._job_handle, process_handle):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            self._kernel32.CloseHandle(process_handle)

    @staticmethod
    def _load_kernel32() -> ctypes.WinDLL:
        if sys.platform != "win32":
            raise NotImplementedError("Windows Job Objects exist only on Windows.")
        kernel32: ctypes.WinDLL = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, ctypes.c_wchar_p)
        kernel32.CreateJobObjectW.restype = ctypes.c_void_p
        kernel32.SetInformationJobObject.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32)
        kernel32.SetInformationJobObject.restype = ctypes.c_int
        kernel32.OpenProcess.argtypes = (ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32)
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.AssignProcessToJobObject.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
        kernel32.AssignProcessToJobObject.restype = ctypes.c_int
        kernel32.TerminateJobObject.argtypes = (ctypes.c_void_p, ctypes.c_uint32)
        kernel32.TerminateJobObject.restype = ctypes.c_int
        kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
        kernel32.CloseHandle.restype = ctypes.c_int
        return kernel32
