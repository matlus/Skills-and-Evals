import errno
import json
import re
from pathlib import Path
from typing import Final

import pytest
from acceptance_support.artifact_recorder import ArtifactRecorder
from acceptance_support.asserters.claude_invocation_asserter import ClaudeInvocationAsserter, ExpectedClaudeInvocation
from acceptance_support.asserters.codex_invocation_asserter import CodexInvocationAsserter, ExpectedCodexInvocation
from acceptance_support.asserters.exception_asserter import ExceptionAsserter
from acceptance_support.asserters.scorecard_asserter import ExpectedScorecard, ExpectedScorecardRow, ScorecardAsserter
from acceptance_support.expected_scorecard_rows import create_expected_rows_for_every_check, interleave_rows_by_check
from acceptance_support.random_data_generator import RandomDataGenerator
from acceptance_support.sample_eval_suite_builder import (
    BASELINE_VARIANT_NAME,
    CANDIDATE_VARIANT_NAME,
    CHECK_NAMES_IN_SUITE_ORDER,
    CODE_EXECUTED_CHECK_NAME,
    FACT_EXTRACTION_SCHEMA_FILE,
    SampleEvalSuite,
    SampleEvalSuiteBuilder,
)
from acceptance_support.scripted_cli_sessions import (
    ScriptedClaudeEventStreamSession,
    ScriptedClaudeToolCall,
    ScriptedCodexCommandExecution,
    ScriptedCodexEventStreamSession,
    ScriptedCodexFileChange,
    ScriptedFailedStartSession,
    ScriptedRawOutputSession,
    ScriptedTimedOutSession,
)
from acceptance_support.scripted_grader_sessions import (
    FACT_EXTRACTION_PROMPT_HEADING,
    JUDGMENT_PROMPT_HEADING,
    create_judge_verdict_schema_document,
    script_correct_grading,
)
from acceptance_support.service_locator_testing import create_domain_facade
from acceptance_support.test_mediator_coding_assistant_cli import (
    CLAUDE_EXECUTABLE_PATH,
    CODEX_EXECUTABLE_PATH,
    CapturedCliInvocation,
    TestMediatorCodingAssistantCli,
)

from prompt_evals import (
    CodingAssistant,
    ConfigurationSettingBlankException,
    DomainFacade,
    EffortLevel,
    EvaluationRequest,
    LlmCliProcessContainmentFailedException,
    LlmCliProcessResumeFailedException,
    LlmCliStartFailedException,
    Scorecard,
)
from prompt_evals.managers.exceptions.process_runner_exceptions import (
    ProcessContainmentFailedException,
    ProcessResumeFailedException,
    ProcessStartFailedException,
)

BASELINE_PROMPT_MARKER: Final[str] = "Baseline prompt."
CANDIDATE_PROMPT_MARKER: Final[str] = "Candidate prompt."
CLAUDE_EXECUTABLE_VARIABLE: Final[str] = "PROMPT_EVALS_CLAUDE_EXECUTABLE"
CODEX_EXECUTABLE_VARIABLE: Final[str] = "PROMPT_EVALS_CODEX_EXECUTABLE"
SESSION_TIMEOUT_SECONDS_VARIABLE: Final[str] = "PROMPT_EVALS_SESSION_TIMEOUT_SECONDS"
GRADER_ASSISTANT_VARIABLE: Final[str] = "PROMPT_EVALS_GRADER_ASSISTANT"
GRADER_MODEL_VARIABLE: Final[str] = "PROMPT_EVALS_GRADER_MODEL"
GRADER_EFFORT_VARIABLE: Final[str] = "PROMPT_EVALS_GRADER_EFFORT"
SESSION_TIMEOUT_SECONDS: Final[str] = "30"
GRADER_EFFORT: Final[str] = "low"
CODEX_ASSISTANT_NAME: Final[str] = "Codex"
FILE_CHANGE_CHECK_NAME: Final[str] = "file-written"


def create_python_command() -> str:
    # Matches the code-executed check's "\bpython" pattern, so a successful run of it proves "code ran".
    return f"python {RandomDataGenerator.create_random_word()}.py"


def create_codex_trial_session(
    answer_text: str, scripted_codex_command_execution: ScriptedCodexCommandExecution | None = None
) -> ScriptedCodexEventStreamSession:
    # The scripted process is the Codex CLI, so the shell tool appears as a Codex command execution;
    # without one given, the trial runs one python command successfully.
    trial_scripted_codex_command_execution: ScriptedCodexCommandExecution = (
        ScriptedCodexCommandExecution(command=create_python_command())
        if scripted_codex_command_execution is None
        else scripted_codex_command_execution
    )
    return ScriptedCodexEventStreamSession(final_text=answer_text, scripted_codex_tool_calls=(trial_scripted_codex_command_execution,))


def create_claude_code_trial_session(answer_text: str) -> ScriptedClaudeEventStreamSession:
    # The scripted process is the Claude Code CLI, so the shell tool appears under Claude's name for it, "Bash".
    return ScriptedClaudeEventStreamSession(
        final_text=answer_text,
        scripted_claude_tool_calls=(
            ScriptedClaudeToolCall(
                tool_name="Bash", tool_input={"command": create_python_command()}, tool_result_text=RandomDataGenerator.create_random_word()
            ),
        ),
    )


def create_random_grader_model_name() -> str:
    return f"grader-{RandomDataGenerator.create_random_word()}"


def create_override_by_environment_variable_name(grader_model_name: str) -> dict[str, str]:
    return {
        CLAUDE_EXECUTABLE_VARIABLE: CLAUDE_EXECUTABLE_PATH,
        CODEX_EXECUTABLE_VARIABLE: CODEX_EXECUTABLE_PATH,
        SESSION_TIMEOUT_SECONDS_VARIABLE: SESSION_TIMEOUT_SECONDS,
        GRADER_MODEL_VARIABLE: grader_model_name,
        GRADER_EFFORT_VARIABLE: GRADER_EFFORT,
    }


def create_codex_evaluation_request(sample_eval_suite: SampleEvalSuite, repetitions: int, variant_names: tuple[str, ...] = ()) -> EvaluationRequest:
    return EvaluationRequest(
        coding_assistant=CodingAssistant.CODEX,
        eval_suite_directory=sample_eval_suite.eval_suite_directory,
        model_name=f"gpt-{RandomDataGenerator.create_random_word()}",
        effort_level=EffortLevel.HIGH,
        repetitions=repetitions,
        variant_names=variant_names,
    )


def create_errored_rows_for_every_check(failure_reason_phrases: tuple[str, ...]) -> tuple[ExpectedScorecardRow, ...]:
    return tuple(
        ExpectedScorecardRow(
            check_name=check_name,
            variant_name=CANDIDATE_VARIANT_NAME,
            trial_count=1,
            passed_count=0,
            errored_count=1,
            meets_minimum_pass_rate=False,
            failure_reason_phrases=failure_reason_phrases,
        )
        for check_name in CHECK_NAMES_IN_SUITE_ORDER
    )


@pytest.mark.acceptance
class TestRunEvaluationInCodexExpectedPaths:
    async def test_RunEvaluation_WhenEveryCodexTrialAnswersCorrectly_ThenEveryCheckPassesForEveryVariantAndTheGatePasses(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        baseline_answer_text: str = f"Baseline answer {RandomDataGenerator.create_random_sentence()}"
        candidate_answer_text: str = f"Candidate answer {RandomDataGenerator.create_random_sentence()}"
        test_mediator_coding_assistant_cli.script_sessions((BASELINE_PROMPT_MARKER,), create_codex_trial_session(baseline_answer_text))
        test_mediator_coding_assistant_cli.script_sessions((CANDIDATE_PROMPT_MARKER,), create_codex_trial_session(candidate_answer_text))
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        evaluation_request: EvaluationRequest = create_codex_evaluation_request(sample_eval_suite, repetitions=2)
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(
            passes_gate=True,
            expected_scorecard_rows=interleave_rows_by_check(
                create_expected_rows_for_every_check(BASELINE_VARIANT_NAME, trial_count=2, passed_count=2),
                create_expected_rows_for_every_check(CANDIDATE_VARIANT_NAME, trial_count=2, passed_count=2),
            ),
        )

        # Act
        actual_scorecard: Scorecard = await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)

    async def test_RunEvaluation_WhenTrialsRunInCodex_ThenEachTrialIsAnIsolatedCodexSessionThatSeesOnlyTheCaseInputs(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        baseline_answer_text: str = f"Baseline answer {RandomDataGenerator.create_random_sentence()}"
        candidate_answer_text: str = f"Candidate answer {RandomDataGenerator.create_random_sentence()}"
        test_mediator_coding_assistant_cli.script_sessions((BASELINE_PROMPT_MARKER,), create_codex_trial_session(baseline_answer_text))
        test_mediator_coding_assistant_cli.script_sessions((CANDIDATE_PROMPT_MARKER,), create_codex_trial_session(candidate_answer_text))
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        evaluation_request: EvaluationRequest = create_codex_evaluation_request(sample_eval_suite, repetitions=2)
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        # Two variants x one case x two repetitions. The trials use tools, so commands run with automatic approval.
        expected_codex_invocation: ExpectedCodexInvocation = ExpectedCodexInvocation(
            invocation_count=4,
            model_name=evaluation_request.model_name,
            effort_level=evaluation_request.effort_level.value,
            sandbox_mode=None,
            approves_commands=True,
            sandbox_file_names=sample_eval_suite.input_file_names,
            output_schema_document=None,
        )

        # Act
        await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        CodexInvocationAsserter.assert_expected_and_actual_are_equal(
            expected_codex_invocation, test_mediator_coding_assistant_cli.captured_codex_invocations
        )

    async def test_RunEvaluation_WhenTrialsRunInCodex_ThenGradersStillRunInTheirOwnToolLessClaudeCodeSessions(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        grader_model_name: str = create_random_grader_model_name()
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        baseline_answer_text: str = f"Baseline answer {RandomDataGenerator.create_random_sentence()}"
        candidate_answer_text: str = f"Candidate answer {RandomDataGenerator.create_random_sentence()}"
        test_mediator_coding_assistant_cli.script_sessions((BASELINE_PROMPT_MARKER,), create_codex_trial_session(baseline_answer_text))
        test_mediator_coding_assistant_cli.script_sessions((CANDIDATE_PROMPT_MARKER,), create_codex_trial_session(candidate_answer_text))
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        evaluation_request: EvaluationRequest = create_codex_evaluation_request(sample_eval_suite, repetitions=1)
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(grader_model_name)
        )
        # Two Codex trials, each graded in Claude Code by one fact extraction and one judgment.
        expected_claude_invocation: ExpectedClaudeInvocation = ExpectedClaudeInvocation(
            invocation_count=4,
            model_name=grader_model_name,
            effort_level=GRADER_EFFORT,
            tool_names_argument="",
            sandbox_file_names=(),
            has_structured_output_schema=True,
            allowed_tools_argument=None,
        )

        # Act
        await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ClaudeInvocationAsserter.assert_expected_and_actual_are_equal(
            expected_claude_invocation, test_mediator_coding_assistant_cli.captured_claude_invocations
        )

    async def test_RunEvaluation_WhenGradersRunInCodex_ThenEachGraderIsAReadOnlyCodexSessionWhoseSchemaFileIsOutsideTheSandbox(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        grader_model_name: str = create_random_grader_model_name()
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        baseline_answer_text: str = f"Baseline answer {RandomDataGenerator.create_random_sentence()}"
        candidate_answer_text: str = f"Candidate answer {RandomDataGenerator.create_random_sentence()}"
        test_mediator_coding_assistant_cli.script_sessions((BASELINE_PROMPT_MARKER,), create_codex_trial_session(baseline_answer_text))
        test_mediator_coding_assistant_cli.script_sessions((CANDIDATE_PROMPT_MARKER,), create_codex_trial_session(candidate_answer_text))
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        evaluation_request: EvaluationRequest = create_codex_evaluation_request(sample_eval_suite, repetitions=1)
        override_by_environment_variable_name: dict[str, str] = create_override_by_environment_variable_name(grader_model_name)
        override_by_environment_variable_name[GRADER_ASSISTANT_VARIABLE] = CodingAssistant.CODEX.value
        domain_facade: DomainFacade = create_domain_facade(test_mediator_coding_assistant_cli, override_by_environment_variable_name)
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(
            passes_gate=True,
            expected_scorecard_rows=interleave_rows_by_check(
                create_expected_rows_for_every_check(BASELINE_VARIANT_NAME, trial_count=1, passed_count=1),
                create_expected_rows_for_every_check(CANDIDATE_VARIANT_NAME, trial_count=1, passed_count=1),
            ),
        )
        expected_grader_sandbox_mode: str = "read-only"
        # One fact extraction per trial; it answers through the eval suite's fact-extraction schema.
        expected_extraction_codex_invocation: ExpectedCodexInvocation = ExpectedCodexInvocation(
            invocation_count=2,
            model_name=grader_model_name,
            effort_level=GRADER_EFFORT,
            sandbox_mode=expected_grader_sandbox_mode,
            approves_commands=False,
            sandbox_file_names=(),
            output_schema_document=json.loads((sample_eval_suite.eval_suite_directory / FACT_EXTRACTION_SCHEMA_FILE).read_text(encoding="utf-8")),
        )
        # One judgment per trial; it answers through the judge verdict schema.
        expected_judgment_codex_invocation: ExpectedCodexInvocation = ExpectedCodexInvocation(
            invocation_count=2,
            model_name=grader_model_name,
            effort_level=GRADER_EFFORT,
            sandbox_mode=expected_grader_sandbox_mode,
            approves_commands=False,
            sandbox_file_names=(),
            output_schema_document=create_judge_verdict_schema_document(),
        )

        # Act
        actual_scorecard: Scorecard = await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        actual_extraction_captured_cli_invocations: tuple[CapturedCliInvocation, ...] = tuple(
            captured_codex_invocation
            for captured_codex_invocation in test_mediator_coding_assistant_cli.captured_codex_invocations
            if captured_codex_invocation.prompt_text.startswith(FACT_EXTRACTION_PROMPT_HEADING)
        )
        actual_judgment_captured_cli_invocations: tuple[CapturedCliInvocation, ...] = tuple(
            captured_codex_invocation
            for captured_codex_invocation in test_mediator_coding_assistant_cli.captured_codex_invocations
            if captured_codex_invocation.prompt_text.startswith(JUDGMENT_PROMPT_HEADING)
        )
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)
        CodexInvocationAsserter.assert_expected_and_actual_are_equal(expected_extraction_codex_invocation, actual_extraction_captured_cli_invocations)
        CodexInvocationAsserter.assert_expected_and_actual_are_equal(expected_judgment_codex_invocation, actual_judgment_captured_cli_invocations)


@pytest.mark.acceptance
class TestRunEvaluationInCodexGradingOutcomes:
    @pytest.mark.parametrize(
        ("exit_code", "command_execution_status"),
        [(1, "failed"), (2, "completed"), (None, "in_progress")],
        ids=["failed", "completed-with-non-zero-exit", "never-completed"],
    )
    async def test_RunEvaluation_WhenTheOnlyPythonCommandDidNotSucceed_ThenTheCodeExecutedCheckFails(
        self, tmp_path: Path, exit_code: int | None, command_execution_status: str
    ) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        candidate_answer_text: str = f"Candidate answer {RandomDataGenerator.create_random_sentence()}"
        unsuccessful_scripted_codex_command_execution: ScriptedCodexCommandExecution = ScriptedCodexCommandExecution(
            command=create_python_command(),
            aggregated_output=RandomDataGenerator.create_random_sentence(),
            exit_code=exit_code,
            execution_status=command_execution_status,
        )
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions(
            (CANDIDATE_PROMPT_MARKER,), create_codex_trial_session(candidate_answer_text, unsuccessful_scripted_codex_command_execution)
        )
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        evaluation_request: EvaluationRequest = create_codex_evaluation_request(
            sample_eval_suite, repetitions=1, variant_names=(CANDIDATE_VARIANT_NAME,)
        )
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        expected_candidate_scorecard_rows: list[ExpectedScorecardRow] = create_expected_rows_for_every_check(
            CANDIDATE_VARIANT_NAME, trial_count=1, passed_count=1
        )
        expected_candidate_scorecard_rows[2] = ExpectedScorecardRow(
            check_name=CODE_EXECUTED_CHECK_NAME,
            variant_name=CANDIDATE_VARIANT_NAME,
            trial_count=1,
            passed_count=0,
            errored_count=0,
            meets_minimum_pass_rate=False,
            failure_reason_phrases=("0 successful of 1 shell calls",),
        )
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(passes_gate=False, expected_scorecard_rows=tuple(expected_candidate_scorecard_rows))

        # Act
        actual_scorecard: Scorecard = await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)

    @pytest.mark.parametrize(
        ("change_kind", "tool_kind"),
        [("add", "write_file"), ("update", "edit_file"), ("delete", "edit_file")],
        ids=["add-is-write-file", "update-is-edit-file", "delete-is-edit-file"],
    )
    async def test_RunEvaluation_WhenCodexChangesAFile_ThenAToolUseCheckOnTheMatchingToolKindAndPathPasses(
        self, tmp_path: Path, change_kind: str, tool_kind: str
    ) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        changed_file_name: str = f"{RandomDataGenerator.create_random_word()}.md"
        eval_suite_definition: dict[str, object] = SampleEvalSuiteBuilder.create_eval_suite_definition()
        eval_suite_definition["trial_tool_kinds"] = ["shell", tool_kind]
        eval_suite_definition["checks"] = [
            {
                "check_name": FILE_CHANGE_CHECK_NAME,
                "grader": "tool_use",
                "tool_kind": tool_kind,
                "tool_input_pattern": re.escape(changed_file_name),
                "minimum_pass_rate": 1.0,
                "description": RandomDataGenerator.create_random_sentence(),
            },
        ]
        SampleEvalSuiteBuilder.write_eval_suite_definition(sample_eval_suite.eval_suite_directory, eval_suite_definition)
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions(
            (CANDIDATE_PROMPT_MARKER,),
            ScriptedCodexEventStreamSession(
                final_text=f"Candidate answer {RandomDataGenerator.create_random_sentence()}",
                scripted_codex_tool_calls=(ScriptedCodexFileChange(file_path=changed_file_name, change_kind=change_kind),),
            ),
        )
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        evaluation_request: EvaluationRequest = create_codex_evaluation_request(
            sample_eval_suite, repetitions=1, variant_names=(CANDIDATE_VARIANT_NAME,)
        )
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(
            passes_gate=True,
            expected_scorecard_rows=(
                ExpectedScorecardRow(
                    check_name=FILE_CHANGE_CHECK_NAME,
                    variant_name=CANDIDATE_VARIANT_NAME,
                    trial_count=1,
                    passed_count=1,
                    errored_count=0,
                    meets_minimum_pass_rate=True,
                ),
            ),
        )

        # Act
        actual_scorecard: Scorecard = await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)


@pytest.mark.acceptance
class TestRunEvaluationInCodexFailurePaths:
    async def test_RunEvaluation_WhenTheCodexTurnFails_ThenTheTrialIsErroredWithTheProviderMessage(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        provider_message: str = f"The model is not supported {RandomDataGenerator.create_random_word()}."
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        # Codex prints the failed turn on stdout and exits with 1.
        test_mediator_coding_assistant_cli.script_sessions(
            (CANDIDATE_PROMPT_MARKER,), ScriptedCodexEventStreamSession(is_error=True, error_messages=(provider_message,), exit_code=1)
        )
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        evaluation_request: EvaluationRequest = create_codex_evaluation_request(
            sample_eval_suite, repetitions=1, variant_names=(CANDIDATE_VARIANT_NAME,)
        )
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(
            passes_gate=False,
            expected_scorecard_rows=create_errored_rows_for_every_check(
                (CODEX_ASSISTANT_NAME, evaluation_request.model_name, "ended in error (turn.failed)", provider_message)
            ),
        )

        # Act
        actual_scorecard: Scorecard = await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)

    async def test_RunEvaluation_WhenCodexExitsNonZeroWithoutAReadableFailure_ThenTheTrialIsErroredWithItsStandardError(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        standard_error_text: str = f"Error: {RandomDataGenerator.create_random_sentence()}"
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions(
            (CANDIDATE_PROMPT_MARKER,), ScriptedRawOutputSession(raw_standard_output_text="", exit_code=2, standard_error_text=standard_error_text)
        )
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        evaluation_request: EvaluationRequest = create_codex_evaluation_request(
            sample_eval_suite, repetitions=1, variant_names=(CANDIDATE_VARIANT_NAME,)
        )
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(
            passes_gate=False,
            expected_scorecard_rows=create_errored_rows_for_every_check((CODEX_ASSISTANT_NAME, "exited with code 2", standard_error_text)),
        )

        # Act
        actual_scorecard: Scorecard = await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)

    async def test_RunEvaluation_WhenTheCodexStreamEndsWithoutCompletingTheTurn_ThenTheTrialIsErroredAsUnreadable(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        truncated_event_stream_text: str = '{"type":"thread.started","thread_id":"0199a213"}\n{"type":"turn.started"}\n'
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions(
            (CANDIDATE_PROMPT_MARKER,), ScriptedRawOutputSession(raw_standard_output_text=truncated_event_stream_text)
        )
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        evaluation_request: EvaluationRequest = create_codex_evaluation_request(
            sample_eval_suite, repetitions=1, variant_names=(CANDIDATE_VARIANT_NAME,)
        )
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(
            passes_gate=False,
            expected_scorecard_rows=create_errored_rows_for_every_check(("could not be read", "expected exactly one turn.completed event, found 0")),
        )

        # Act
        actual_scorecard: Scorecard = await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)

    async def test_RunEvaluation_WhenACodexTrialTimesOut_ThenTheTrialIsErroredWithTheTimeout(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions((CANDIDATE_PROMPT_MARKER,), ScriptedTimedOutSession())
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        evaluation_request: EvaluationRequest = create_codex_evaluation_request(
            sample_eval_suite, repetitions=1, variant_names=(CANDIDATE_VARIANT_NAME,)
        )
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(
            passes_gate=False,
            expected_scorecard_rows=create_errored_rows_for_every_check(
                (CODEX_ASSISTANT_NAME, f"did not finish within {SESSION_TIMEOUT_SECONDS} seconds")
            ),
        )

        # Act
        actual_scorecard: Scorecard = await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)

    @pytest.mark.parametrize(
        "start_error",
        [FileNotFoundError(errno.ENOENT, "No such file or directory"), PermissionError(errno.EACCES, "Permission denied")],
        ids=["missing", "not-executable"],
    )
    async def test_RunEvaluation_WhenTheCodexCliCannotBeStarted_ThenLlmCliStartFailedExceptionNamesTheSettingAndStopsTheEvaluation(
        self, tmp_path: Path, start_error: OSError
    ) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions(
            (CANDIDATE_PROMPT_MARKER,),
            ScriptedFailedStartSession(raised_exception=ProcessStartFailedException(CODEX_EXECUTABLE_PATH, start_error)),
        )
        evaluation_request: EvaluationRequest = create_codex_evaluation_request(
            sample_eval_suite, repetitions=1, variant_names=(CANDIDATE_VARIANT_NAME,)
        )
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        expected_message_phrases: tuple[str, ...] = ("could not be started", "Install Codex", CODEX_EXECUTABLE_VARIABLE)
        expected_contextual_entries_by_name: dict[str, object] = {
            "AssistantName": CODEX_ASSISTANT_NAME,
            "ExecutablePath": CODEX_EXECUTABLE_PATH,
            "StartFailure": f"{type(start_error).__name__}: {start_error}",
            "ExceptionType": LlmCliStartFailedException.__name__,
        }

        # Act
        with pytest.raises(LlmCliStartFailedException) as exception_info:
            await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=LlmCliStartFailedException,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_prompt_evals_base_exception=exception_info.value,
        )

    async def test_RunEvaluation_WhenTheStartedCodexProcessCannotBeContained_ThenLlmCliProcessContainmentFailedExceptionStopsTheEvaluation(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        containment_error: PermissionError = PermissionError(RandomDataGenerator.create_random_sentence())
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions(
            (CANDIDATE_PROMPT_MARKER,),
            ScriptedFailedStartSession(
                raised_exception=ProcessContainmentFailedException(RandomDataGenerator.create_random_process_id(), containment_error)
            ),
        )
        evaluation_request: EvaluationRequest = create_codex_evaluation_request(
            sample_eval_suite, repetitions=1, variant_names=(CANDIDATE_VARIANT_NAME,)
        )
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        expected_message_phrases: tuple[str, ...] = (CODEX_ASSISTANT_NAME, evaluation_request.model_name, "could not be contained")
        # The process did start, so the exception must not send the user to reinstall Codex or change its executable setting.
        unexpected_message_phrases: tuple[str, ...] = ("could not be started", "Install Codex", CODEX_EXECUTABLE_VARIABLE)
        expected_contextual_entries_by_name: dict[str, object] = {
            "AssistantName": CODEX_ASSISTANT_NAME,
            "ModelName": evaluation_request.model_name,
            "ContainmentFailure": f"{type(containment_error).__name__}: {containment_error}",
            "ExceptionType": LlmCliProcessContainmentFailedException.__name__,
        }

        # Act
        with pytest.raises(LlmCliProcessContainmentFailedException) as exception_info:
            await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=LlmCliProcessContainmentFailedException,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_prompt_evals_base_exception=exception_info.value,
            unexpected_message_phrases=unexpected_message_phrases,
        )

    async def test_RunEvaluation_WhenTheStartedCodexProcessCannotBeResumed_ThenLlmCliProcessResumeFailedExceptionStopsTheEvaluation(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        resume_error: PermissionError = PermissionError(RandomDataGenerator.create_random_sentence())
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions(
            (CANDIDATE_PROMPT_MARKER,),
            ScriptedFailedStartSession(raised_exception=ProcessResumeFailedException(RandomDataGenerator.create_random_process_id(), resume_error)),
        )
        evaluation_request: EvaluationRequest = create_codex_evaluation_request(
            sample_eval_suite, repetitions=1, variant_names=(CANDIDATE_VARIANT_NAME,)
        )
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        expected_message_phrases: tuple[str, ...] = (CODEX_ASSISTANT_NAME, evaluation_request.model_name, "could not be resumed")
        # The process was created, so the exception must not send the user to reinstall Codex or change its executable setting.
        unexpected_message_phrases: tuple[str, ...] = ("could not be started", "Install Codex", CODEX_EXECUTABLE_VARIABLE)
        expected_contextual_entries_by_name: dict[str, object] = {
            "AssistantName": CODEX_ASSISTANT_NAME,
            "ModelName": evaluation_request.model_name,
            "ResumeFailure": f"{type(resume_error).__name__}: {resume_error}",
            "ExceptionType": LlmCliProcessResumeFailedException.__name__,
        }

        # Act
        with pytest.raises(LlmCliProcessResumeFailedException) as exception_info:
            await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=LlmCliProcessResumeFailedException,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_prompt_evals_base_exception=exception_info.value,
            unexpected_message_phrases=unexpected_message_phrases,
        )


@pytest.mark.acceptance
class TestRunEvaluationInCodexInvalidConfiguration:
    async def test_RunEvaluation_WhenTheCodexExecutableSettingIsBlank_ThenConfigurationSettingBlankExceptionNamesTheSetting(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        blank_setting_value: str = "  "
        override_by_environment_variable_name: dict[str, str] = create_override_by_environment_variable_name(create_random_grader_model_name())
        override_by_environment_variable_name[CODEX_EXECUTABLE_VARIABLE] = blank_setting_value
        # Only an evaluation that runs Codex reads the Codex settings, so a Claude Code user is not stopped by them; the
        # test after this one proves that half.
        domain_facade: DomainFacade = create_domain_facade(TestMediatorCodingAssistantCli(), override_by_environment_variable_name)
        evaluation_request: EvaluationRequest = create_codex_evaluation_request(sample_eval_suite, repetitions=1)
        expected_message_phrases: tuple[str, ...] = (CODEX_EXECUTABLE_VARIABLE, "expected a non-blank value")
        expected_contextual_entries_by_name: dict[str, object] = {
            "EnvironmentVariableName": CODEX_EXECUTABLE_VARIABLE,
            "ConfiguredValue": blank_setting_value,
        }

        # Act
        with pytest.raises(ConfigurationSettingBlankException) as exception_info:
            await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=ConfigurationSettingBlankException,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_prompt_evals_base_exception=exception_info.value,
        )

    async def test_RunEvaluation_WhenTheCodexExecutableSettingIsBlankButNothingRunsInCodex_ThenTheClaudeCodeEvaluationCompletes(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        candidate_answer_text: str = f"Candidate answer {RandomDataGenerator.create_random_sentence()}"
        test_mediator_coding_assistant_cli.script_sessions((CANDIDATE_PROMPT_MARKER,), create_claude_code_trial_session(candidate_answer_text))
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        override_by_environment_variable_name: dict[str, str] = create_override_by_environment_variable_name(create_random_grader_model_name())
        override_by_environment_variable_name[CODEX_EXECUTABLE_VARIABLE] = "  "
        domain_facade: DomainFacade = create_domain_facade(test_mediator_coding_assistant_cli, override_by_environment_variable_name)
        # The trials and, by default, the graders run in Claude Code.
        evaluation_request: EvaluationRequest = EvaluationRequest(
            coding_assistant=CodingAssistant.CLAUDE_CODE,
            eval_suite_directory=sample_eval_suite.eval_suite_directory,
            model_name=f"model-{RandomDataGenerator.create_random_word()}",
            effort_level=EffortLevel.MEDIUM,
            repetitions=1,
            variant_names=(CANDIDATE_VARIANT_NAME,),
        )
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(
            passes_gate=True,
            expected_scorecard_rows=tuple(create_expected_rows_for_every_check(CANDIDATE_VARIANT_NAME, trial_count=1, passed_count=1)),
        )

        # Act
        actual_scorecard: Scorecard = await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)
