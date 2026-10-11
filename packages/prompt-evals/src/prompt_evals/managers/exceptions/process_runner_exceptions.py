"""Why the process runner, the wire under every coding-assistant CLI gateway, could not run a process.

The runner does not know which CLI it ran, so each gateway translates these into an exception that names its CLI.
"""

from abc import ABC
from typing import final

from prompt_evals.managers.exceptions.prompt_evals_exceptions import ContextualDataDict, PromptEvalsTechnicalBaseException


class ProcessRunnerBaseException(PromptEvalsTechnicalBaseException, ABC):
    def __init__(self, failure_summary: str, operating_system_error: OSError, failure_contextual_data_by_name: ContextualDataDict) -> None:
        operating_system_error_description: str = ProcessRunnerBaseException._describe_operating_system_error(operating_system_error)
        super().__init__(
            f"{failure_summary} ({operating_system_error_description}).",
            {**failure_contextual_data_by_name, "OperatingSystemError": operating_system_error_description},
        )
        self._operating_system_error_description: str = operating_system_error_description

    @property
    def operating_system_error_description(self) -> str:
        return self._operating_system_error_description

    @staticmethod
    def _describe_operating_system_error(operating_system_error: OSError) -> str:
        operating_system_error_type_name: str = type(operating_system_error).__name__
        # asyncio raises its timeout with no text, which would otherwise leave a dangling "TimeoutError: ".
        if not str(operating_system_error):
            return operating_system_error_type_name
        return f"{operating_system_error_type_name}: {operating_system_error}"


@final
class ProcessStartFailedException(ProcessRunnerBaseException):
    """Creating the process failed: the executable is missing, not executable, or not a valid program for this platform."""

    def __init__(self, executable_path: str, operating_system_error: OSError) -> None:
        super().__init__(f"The executable '{executable_path}' could not be started", operating_system_error, {"ExecutablePath": executable_path})


@final
class ProcessContainmentFailedException(ProcessRunnerBaseException):
    """The process started, but could not be placed in the container that ends every process it starts."""

    def __init__(self, process_id: int, operating_system_error: OSError) -> None:
        super().__init__(
            f"Process {process_id} started but could not be contained with the processes it starts",
            operating_system_error,
            {"ProcessId": process_id},
        )


@final
class ProcessResumeFailedException(ProcessRunnerBaseException):
    """The process started suspended and was contained, but could not be resumed, so it would never run."""

    def __init__(self, process_id: int, operating_system_error: OSError) -> None:
        super().__init__(
            f"Process {process_id} started suspended and was contained but could not be resumed",
            operating_system_error,
            {"ProcessId": process_id},
        )


@final
class ProcessTimedOutException(ProcessRunnerBaseException):
    """The process did not finish within its timeout. The runner ends it, and every process it started, before raising this."""

    def __init__(self, process_id: int, timeout_seconds: float, timeout_error: TimeoutError) -> None:
        super().__init__(
            f"Process {process_id} did not finish within {timeout_seconds:g} seconds",
            timeout_error,
            {"ProcessId": process_id, "TimeoutSeconds": timeout_seconds},
        )
