import asyncio
import sys
from pathlib import Path
from typing import Final

import pytest
from acceptance_support.asserters.exception_asserter import ExceptionAsserter
from acceptance_support.random_data_generator import RandomDataGenerator
from acceptance_support.windows_process_probe import WindowsProcessProbe

from prompt_evals.managers.exceptions.process_runner_exceptions import ProcessStartFailedException, ProcessTimedOutException
from prompt_evals.managers.gateways.process_runners.process_runner_asyncio import ProcessRunnerAsyncio
from prompt_evals.managers.gateways.process_runners.process_runner_models import ProcessInvocation, ProcessOutcome

PYTHON_EXECUTABLE_PATH: Final[str] = sys.executable
OPERATING_SYSTEM_ERROR_CONTEXT_NAME: Final[str] = "OperatingSystemError"
PROCESS_ID_CONTEXT_NAME: Final[str] = "ProcessId"
# Long enough to start a Python process that starts another one, short enough to keep the test quick.
SHORT_TIMEOUT_SECONDS: Final[float] = 5.0
GRANDCHILD_EXIT_WAIT_SECONDS: Final[float] = 10.0
SLEEP_LONGER_THAN_ANY_TIMEOUT_SCRIPT: Final[str] = "import time; time.sleep(120)"


@pytest.mark.class_test
class TestProcessRunnerAsyncio:
    async def test_RunProcess_WhenTheProcessEchoesItsStandardInput_ThenTheOutcomeCarriesItsOutputAndExitCode(self, tmp_path: Path) -> None:
        # Arrange
        standard_input_text: str = RandomDataGenerator.create_random_word()
        expected_exit_code: int = 3
        process_invocation: ProcessInvocation = ProcessInvocation(
            command_arguments=(
                PYTHON_EXECUTABLE_PATH,
                "-c",
                f"import sys; sys.stdout.write(sys.stdin.read().upper()); sys.exit({expected_exit_code})",
            ),
            standard_input_text=standard_input_text,
            working_directory=tmp_path,
            timeout_seconds=60.0,
        )
        expected_process_outcome: ProcessOutcome = ProcessOutcome(
            exit_code=expected_exit_code, standard_output_text=standard_input_text.upper(), standard_error_text=""
        )

        # Act
        actual_process_outcome: ProcessOutcome = await ProcessRunnerAsyncio().run_process(process_invocation)

        # Assert
        assert actual_process_outcome == expected_process_outcome, (
            "a process the runner starts (suspended and then resumed on Windows) must read its standard input and report "
            f"its output and exit code; expected {expected_process_outcome!r}, actual {actual_process_outcome!r}"
        )

    async def test_RunProcess_WhenTheExecutableDoesNotExist_ThenProcessStartFailedExceptionNamesTheExecutable(self, tmp_path: Path) -> None:
        # Arrange
        missing_executable_path: str = str(tmp_path / f"missing-{RandomDataGenerator.create_random_word()}")
        process_invocation: ProcessInvocation = ProcessInvocation(
            command_arguments=(missing_executable_path, "--version"),
            standard_input_text="",
            working_directory=tmp_path,
            timeout_seconds=30.0,
        )
        expected_message_phrases: tuple[str, ...] = (f"The executable '{missing_executable_path}' could not be started", "FileNotFoundError")
        expected_contextual_entries_by_name: dict[str, object] = {
            "ExecutablePath": missing_executable_path,
            "ExceptionType": ProcessStartFailedException.__name__,
        }
        # The operating system's error text differs between platforms, so only its presence is checked.
        expected_contextual_entry_names: tuple[str, ...] = (OPERATING_SYSTEM_ERROR_CONTEXT_NAME,)

        # Act
        with pytest.raises(ProcessStartFailedException) as exception_info:
            await ProcessRunnerAsyncio().run_process(process_invocation)

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=ProcessStartFailedException,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_prompt_evals_base_exception=exception_info.value,
            expected_contextual_entry_names=expected_contextual_entry_names,
        )

    async def test_RunProcess_WhenTheProcessOutlivesItsTimeout_ThenProcessTimedOutExceptionCarriesTheTimeout(self, tmp_path: Path) -> None:
        # Arrange
        process_invocation: ProcessInvocation = ProcessInvocation(
            command_arguments=(PYTHON_EXECUTABLE_PATH, "-c", SLEEP_LONGER_THAN_ANY_TIMEOUT_SCRIPT),
            standard_input_text="",
            working_directory=tmp_path,
            timeout_seconds=SHORT_TIMEOUT_SECONDS,
        )
        expected_message_phrases: tuple[str, ...] = (f"did not finish within {SHORT_TIMEOUT_SECONDS:g} seconds", "(TimeoutError)")
        expected_contextual_entries_by_name: dict[str, object] = {
            "TimeoutSeconds": SHORT_TIMEOUT_SECONDS,
            OPERATING_SYSTEM_ERROR_CONTEXT_NAME: "TimeoutError",
            "ExceptionType": ProcessTimedOutException.__name__,
        }
        # The operating system assigns the process id when the process starts.
        expected_contextual_entry_names: tuple[str, ...] = (PROCESS_ID_CONTEXT_NAME,)

        # Act
        with pytest.raises(ProcessTimedOutException) as exception_info:
            await ProcessRunnerAsyncio().run_process(process_invocation)

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=ProcessTimedOutException,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_prompt_evals_base_exception=exception_info.value,
            expected_contextual_entry_names=expected_contextual_entry_names,
        )

    @pytest.mark.skipif(sys.platform != "win32", reason="The Job Object containment this test verifies exists only on Windows.")
    async def test_RunProcess_WhenAProcessTheChildStartedAtOnceOutlivesTheTimeout_ThenThatProcessIsEndedWithTheChild(self, tmp_path: Path) -> None:
        # Arrange
        grandchild_process_id_file: Path = tmp_path / "grandchild_process_id.txt"
        grandchild_script: str = (
            f"import os, pathlib, time; pathlib.Path({str(grandchild_process_id_file)!r}).write_text(str(os.getpid())); time.sleep(120)"
        )
        # Like a launcher shim, the child starts its own child before it reads any standard input.
        child_script: str = f"import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', {grandchild_script!r}]); time.sleep(120)"
        process_invocation: ProcessInvocation = ProcessInvocation(
            command_arguments=(PYTHON_EXECUTABLE_PATH, "-c", child_script),
            standard_input_text="",
            working_directory=tmp_path,
            timeout_seconds=SHORT_TIMEOUT_SECONDS,
        )

        # Act
        with pytest.raises(ProcessTimedOutException):
            await ProcessRunnerAsyncio().run_process(process_invocation)

        # Assert
        grandchild_process_id: int = int(await asyncio.to_thread(grandchild_process_id_file.read_text, encoding="utf-8"))
        has_grandchild_ended: bool = WindowsProcessProbe.has_process_ended_within(grandchild_process_id, GRANDCHILD_EXIT_WAIT_SECONDS)
        assert has_grandchild_ended, (
            f"the process {grandchild_process_id} that the child started at once must end with the child when the child times out, "
            f"because the child is in its Job Object before it runs; it was still running {GRANDCHILD_EXIT_WAIT_SECONDS:g} seconds later"
        )
