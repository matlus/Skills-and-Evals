import asyncio
import contextlib
import os
import signal
import sys
from typing import Final, final, override

from prompt_evals.managers.exceptions.process_runner_exceptions import (
    ProcessContainmentFailedException,
    ProcessResumeFailedException,
    ProcessStartFailedException,
    ProcessTimedOutException,
)
from prompt_evals.managers.gateways.process_runners.job_objects.windows_job_object import WindowsJobObject
from prompt_evals.managers.gateways.process_runners.job_objects.windows_suspended_process import CREATE_SUSPENDED, WindowsSuspendedProcess
from prompt_evals.managers.gateways.process_runners.process_runner_base import ProcessRunnerBase
from prompt_evals.managers.gateways.process_runners.process_runner_models import ProcessInvocation, ProcessOutcome

TEXT_ENCODING: Final[str] = "utf-8"
# After the kill, a descendant that still holds an inherited output pipe could keep wait() from returning; stop waiting after this.
PROCESS_TREE_CLEANUP_TIMEOUT_SECONDS: Final[float] = 10.0
WINDOWS_PLATFORM: Final[str] = "win32"
NO_CREATION_FLAGS: Final[int] = 0


@final
class ProcessRunnerAsyncio(ProcessRunnerBase):
    @override
    async def run_process(self, process_invocation: ProcessInvocation) -> ProcessOutcome:
        process: asyncio.subprocess.Process = await self._start_process(process_invocation)
        windows_job_object: WindowsJobObject | None = None
        standard_output_bytes: bytes
        standard_error_bytes: bytes
        try:
            # On Windows the process is created suspended and runs no code until it is in the job, so every process it
            # starts, even one a launcher such as a .cmd shim starts at once, joins the job.
            windows_job_object = self._contain_process_tree(process)
            self._resume_process(process)
            standard_output_bytes, standard_error_bytes = await self._communicate_within_timeout(process, process_invocation)
            exit_code: int = await process.wait()
        except BaseException:
            # A timeout can come from a tool command that still holds the output pipe after the CLI itself exited,
            # so the tree is killed whether or not the direct child is still running.
            await self._terminate_process_tree(process, windows_job_object)
            raise
        finally:
            # Ends any tool command the session left behind, so it cannot keep running or keep the sandbox locked.
            self._release_process_tree(process, windows_job_object)
        return self._build_process_outcome(exit_code, standard_output_bytes, standard_error_bytes)

    @staticmethod
    def _is_windows_platform() -> bool:
        return sys.platform == WINDOWS_PLATFORM

    @staticmethod
    async def _start_process(process_invocation: ProcessInvocation) -> asyncio.subprocess.Process:
        # On POSIX the process leads its own process group, so the whole tree it starts can be killed together.
        # On Windows it starts suspended, so it can be placed in its job before it runs.
        is_windows_platform: bool = ProcessRunnerAsyncio._is_windows_platform()
        try:
            return await asyncio.create_subprocess_exec(
                *process_invocation.command_arguments,
                cwd=process_invocation.working_directory,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=not is_windows_platform,
                creationflags=CREATE_SUSPENDED if is_windows_platform else NO_CREATION_FLAGS,
            )
        except OSError as operating_system_error:
            raise ProcessStartFailedException(process_invocation.command_arguments[0], operating_system_error) from operating_system_error

    @staticmethod
    def _contain_process_tree(process: asyncio.subprocess.Process) -> WindowsJobObject | None:
        # POSIX needs no container: the process leads its own process group, which still reaches orphaned descendants.
        if not ProcessRunnerAsyncio._is_windows_platform():
            return None
        try:
            return WindowsJobObject.contain_process(process.pid)
        except OSError as operating_system_error:
            raise ProcessContainmentFailedException(process.pid, operating_system_error) from operating_system_error

    @staticmethod
    def _resume_process(process: asyncio.subprocess.Process) -> None:
        # POSIX starts the process running.
        if not ProcessRunnerAsyncio._is_windows_platform():
            return
        try:
            WindowsSuspendedProcess.resume(process.pid)
        except OSError as operating_system_error:
            raise ProcessResumeFailedException(process.pid, operating_system_error) from operating_system_error

    @staticmethod
    async def _communicate_within_timeout(process: asyncio.subprocess.Process, process_invocation: ProcessInvocation) -> tuple[bytes, bytes]:
        try:
            return await asyncio.wait_for(
                process.communicate(process_invocation.standard_input_text.encode(TEXT_ENCODING)),
                timeout=process_invocation.timeout_seconds,
            )
        except TimeoutError as timeout_error:
            raise ProcessTimedOutException(process.pid, process_invocation.timeout_seconds, timeout_error) from timeout_error

    @staticmethod
    async def _terminate_process_tree(process: asyncio.subprocess.Process, windows_job_object: WindowsJobObject | None) -> None:
        # On a timeout or a cancellation neither the session nor the tool commands it started (for example a hung shell
        # command) may keep running and consuming quota after we stop waiting, nor keep the sandbox directory locked.
        ProcessRunnerAsyncio._kill_process_tree(process, windows_job_object)
        with contextlib.suppress(ProcessLookupError):
            process.kill()
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(process.wait(), timeout=PROCESS_TREE_CLEANUP_TIMEOUT_SECONDS)

    @staticmethod
    def _kill_process_tree(process: asyncio.subprocess.Process, windows_job_object: WindowsJobObject | None) -> None:
        if windows_job_object is not None:
            # A failure here must not replace the exception being handled; closing the job afterwards still ends the tree.
            with contextlib.suppress(OSError):
                windows_job_object.terminate()
        else:
            ProcessRunnerAsyncio._kill_process_group(process)

    @staticmethod
    def _release_process_tree(process: asyncio.subprocess.Process, windows_job_object: WindowsJobObject | None) -> None:
        if windows_job_object is not None:
            # With kill-on-close set, closing the job also ends every process still in it.
            windows_job_object.close()
        else:
            ProcessRunnerAsyncio._kill_process_group(process)

    @staticmethod
    def _kill_process_group(process: asyncio.subprocess.Process) -> None:
        if ProcessRunnerAsyncio._is_windows_platform():
            return
        # The group may already be empty, and cleanup must never replace a result or an exception being raised.
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(process.pid, signal.SIGKILL)

    @staticmethod
    def _build_process_outcome(exit_code: int, standard_output_bytes: bytes, standard_error_bytes: bytes) -> ProcessOutcome:
        return ProcessOutcome(
            exit_code=exit_code,
            standard_output_text=standard_output_bytes.decode(TEXT_ENCODING, errors="replace"),
            standard_error_text=standard_error_bytes.decode(TEXT_ENCODING, errors="replace"),
        )
