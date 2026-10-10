from pathlib import Path
from typing import Final

import pytest
from acceptance_support.artifact_recorder import ArtifactRecorder
from acceptance_support.asserters.claude_invocation_asserter import ClaudeInvocationAsserter, ExpectedClaudeInvocation
from acceptance_support.asserters.exception_asserter import ExceptionAsserter
from acceptance_support.asserters.scorecard_asserter import ExpectedScorecard, ExpectedScorecardRow, ScorecardAsserter
from acceptance_support.expected_scorecard_rows import create_expected_rows_for_every_check, interleave_rows_by_check
from acceptance_support.random_data_generator import RandomDataGenerator
from acceptance_support.sample_eval_suite_builder import (
    BASELINE_PROMPT_FILE,
    BASELINE_VARIANT_NAME,
    CANDIDATE_PROMPT_FILE,
    CANDIDATE_VARIANT_NAME,
    CASE_EXPECTED_FACTS_FILE,
    CASE_INPUTS_DIRECTORY,
    CASE_NAME,
    CHECK_NAMES_IN_SUITE_ORDER,
    CODE_EXECUTED_CHECK_NAME,
    EXPECTED_FACTS_FILE_NAME,
    STATUS_FACT_NAME,
    STATUS_VALUE_CHECK_NAME,
    TABLES_FIRST_CHECK_NAME,
    TABLES_FIRST_RUBRIC_FILE,
    TOTAL_AMOUNT_CHECK_NAME,
    TOTAL_FACT_NAME,
    SampleEvalSuite,
    SampleEvalSuiteBuilder,
)
from acceptance_support.scripted_cli_sessions import (
    ScriptedClaudeToolCall,
    ScriptedEventStreamSession,
    ScriptedFailedStartSession,
    ScriptedRawOutputSession,
)
from acceptance_support.scripted_grader_sessions import (
    FACT_EXTRACTION_PROMPT_HEADING,
    JUDGMENT_PROMPT_HEADING,
    create_extraction_session,
    create_judge_session,
    script_correct_grading,
)
from acceptance_support.service_locator_testing import ServiceLocatorTesting, create_domain_facade
from acceptance_support.test_mediator_coding_assistant_cli import CapturedCliInvocation, TestMediatorCodingAssistantCli

from prompt_evals import (
    ArtifactCallbackException,
    CodingAssistant,
    ConfigurationSettingException,
    DomainFacade,
    EffortLevel,
    EvalSuiteDefinitionInvalidException,
    EvalSuiteNotFoundException,
    EvaluationArtifact,
    EvaluationArtifactType,
    EvaluationRequest,
    EvaluationRequestValidationException,
    LlmCliStartFailedException,
    Scorecard,
    ScorecardRow,
    ScorecardValidationException,
    TrialIdentity,
)

BASELINE_PROMPT_MARKER: Final[str] = "Baseline prompt."
CANDIDATE_PROMPT_MARKER: Final[str] = "Candidate prompt."
CLAUDE_EXECUTABLE_VARIABLE: Final[str] = "PROMPT_EVALS_CLAUDE_EXECUTABLE"
SESSION_TIMEOUT_SECONDS_VARIABLE: Final[str] = "PROMPT_EVALS_SESSION_TIMEOUT_SECONDS"
GRADER_MODEL_VARIABLE: Final[str] = "PROMPT_EVALS_GRADER_MODEL"
GRADER_EFFORT_VARIABLE: Final[str] = "PROMPT_EVALS_GRADER_EFFORT"
SESSION_TIMEOUT_SECONDS: Final[str] = "30"
GRADER_EFFORT: Final[str] = "low"
EVAL_SUITE_DEFINITION_FILE_NAME: Final[str] = "eval_suite.json"
VALIDATION_PROBLEM_COUNT_ENTRY_NAME: Final[str] = "ValidationProblemCount"
CLAUDE_CODE_ASSISTANT_NAME: Final[str] = "Claude Code"


def create_trial_session(answer_text: str, *, ran_python: bool = True, shell_command: str = "python totals.py") -> ScriptedEventStreamSession:
    # The scripted process is the Claude Code CLI, so the shell tool appears under Claude's name for it, "Bash".
    scripted_tool_calls: tuple[ScriptedClaudeToolCall, ...] = (
        (ScriptedClaudeToolCall(tool_name="Bash", tool_input={"command": shell_command}, tool_result_text=RandomDataGenerator.create_random_word()),)
        if ran_python
        else ()
    )
    return ScriptedEventStreamSession(final_text=answer_text, scripted_tool_calls=scripted_tool_calls)


def create_random_grader_model_name() -> str:
    return f"grader-{RandomDataGenerator.create_random_word()}"


def create_override_by_environment_variable_name(grader_model_name: str) -> dict[str, str]:
    return {
        CLAUDE_EXECUTABLE_VARIABLE: "claude",
        SESSION_TIMEOUT_SECONDS_VARIABLE: SESSION_TIMEOUT_SECONDS,
        GRADER_MODEL_VARIABLE: grader_model_name,
        GRADER_EFFORT_VARIABLE: GRADER_EFFORT,
    }


def create_evaluation_request(sample_eval_suite: SampleEvalSuite, repetitions: int, variant_names: tuple[str, ...] = ()) -> EvaluationRequest:
    return EvaluationRequest(
        coding_assistant=CodingAssistant.CLAUDE_CODE,
        eval_suite_directory=sample_eval_suite.eval_suite_directory,
        model_name=f"model-{RandomDataGenerator.create_random_word()}",
        effort_level=EffortLevel.MEDIUM,
        repetitions=repetitions,
        variant_names=variant_names,
    )


@pytest.mark.acceptance
class TestRunEvaluationExpectedPaths:
    async def test_RunEvaluation_WhenEveryTrialAnswersCorrectly_ThenEveryCheckPassesForEveryVariantAndTheGatePasses(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        baseline_answer_text: str = f"Baseline answer {RandomDataGenerator.create_random_sentence()}"
        candidate_answer_text: str = f"Candidate answer {RandomDataGenerator.create_random_sentence()}"
        test_mediator_coding_assistant_cli.script_sessions((BASELINE_PROMPT_MARKER,), create_trial_session(baseline_answer_text))
        test_mediator_coding_assistant_cli.script_sessions((CANDIDATE_PROMPT_MARKER,), create_trial_session(candidate_answer_text))
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        evaluation_request: EvaluationRequest = create_evaluation_request(sample_eval_suite, repetitions=2)
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

    async def test_RunEvaluation_WhenTrialsRun_ThenEachTrialIsAnIsolatedSessionThatSeesOnlyTheCaseInputs(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        baseline_answer_text: str = f"Baseline answer {RandomDataGenerator.create_random_sentence()}"
        candidate_answer_text: str = f"Candidate answer {RandomDataGenerator.create_random_sentence()}"
        test_mediator_coding_assistant_cli.script_sessions((BASELINE_PROMPT_MARKER,), create_trial_session(baseline_answer_text))
        test_mediator_coding_assistant_cli.script_sessions((CANDIDATE_PROMPT_MARKER,), create_trial_session(candidate_answer_text))
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        evaluation_request: EvaluationRequest = create_evaluation_request(sample_eval_suite, repetitions=2)
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        # Two variants x one case x two repetitions.
        expected_claude_invocation: ExpectedClaudeInvocation = ExpectedClaudeInvocation(
            invocation_count=4,
            model_name=evaluation_request.model_name,
            effort_level=evaluation_request.effort_level.value,
            tool_names_argument="Bash,Read",
            sandbox_file_names=sample_eval_suite.input_file_names,
            has_structured_output_schema=False,
            allowed_tools_argument="Bash,Read",
        )

        # Act
        await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        actual_trial_invocations: tuple[CapturedCliInvocation, ...] = tuple(
            captured_claude_invocation
            for captured_claude_invocation in test_mediator_coding_assistant_cli.captured_claude_invocations
            if not captured_claude_invocation.prompt_text.startswith("#")
        )
        ClaudeInvocationAsserter.assert_expected_and_actual_are_equal(expected_claude_invocation, actual_trial_invocations)

    async def test_RunEvaluation_WhenAnswersAreGraded_ThenGradersRunInSeparateToolLessSessionsWithTheGraderModel(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        grader_model_name: str = create_random_grader_model_name()
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        baseline_answer_text: str = f"Baseline answer {RandomDataGenerator.create_random_sentence()}"
        candidate_answer_text: str = f"Candidate answer {RandomDataGenerator.create_random_sentence()}"
        test_mediator_coding_assistant_cli.script_sessions((BASELINE_PROMPT_MARKER,), create_trial_session(baseline_answer_text))
        test_mediator_coding_assistant_cli.script_sessions((CANDIDATE_PROMPT_MARKER,), create_trial_session(candidate_answer_text))
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        evaluation_request: EvaluationRequest = create_evaluation_request(sample_eval_suite, repetitions=1)
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(grader_model_name)
        )
        # Two trials, each graded by one fact extraction and one judgment.
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
        actual_grader_invocations: tuple[CapturedCliInvocation, ...] = tuple(
            captured_claude_invocation
            for captured_claude_invocation in test_mediator_coding_assistant_cli.captured_claude_invocations
            if captured_claude_invocation.prompt_text.startswith("#")
        )
        ClaudeInvocationAsserter.assert_expected_and_actual_are_equal(expected_claude_invocation, actual_grader_invocations)

    async def test_RunEvaluation_WhenEvaluationCompletes_ThenEveryTrialArtifactAndTheScorecardAreEmitted(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        baseline_answer_text: str = f"Baseline answer {RandomDataGenerator.create_random_sentence()}"
        candidate_answer_text: str = f"Candidate answer {RandomDataGenerator.create_random_sentence()}"
        test_mediator_coding_assistant_cli.script_sessions((BASELINE_PROMPT_MARKER,), create_trial_session(baseline_answer_text))
        test_mediator_coding_assistant_cli.script_sessions((CANDIDATE_PROMPT_MARKER,), create_trial_session(candidate_answer_text))
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        evaluation_request: EvaluationRequest = create_evaluation_request(sample_eval_suite, repetitions=1)
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        artifact_recorder: ArtifactRecorder = ArtifactRecorder()
        expected_trial_artifact_descriptions: set[tuple[EvaluationArtifactType, TrialIdentity | None, str, str]] = {
            (artifact_type, TrialIdentity(variant_name=variant_name, case_name=CASE_NAME, repetition_number=1), filename_suffix, content_type)
            for variant_name in (BASELINE_VARIANT_NAME, CANDIDATE_VARIANT_NAME)
            for artifact_type, filename_suffix, content_type in (
                (EvaluationArtifactType.TRIAL_EVENT_STREAM, "event_stream.jsonl", "application/x-ndjson"),
                (EvaluationArtifactType.TRIAL_ANSWER, "answer.md", "text/markdown"),
                (EvaluationArtifactType.TRIAL_GRADE, "grade.json", "application/json"),
            )
        }
        expected_run_artifact_descriptions: set[tuple[EvaluationArtifactType, TrialIdentity | None, str, str]] = {
            (EvaluationArtifactType.SCORECARD, None, "scorecard.json", "application/json"),
            (EvaluationArtifactType.SCORECARD_REPORT, None, "scorecard.md", "text/markdown"),
        }
        expected_artifact_descriptions: set[tuple[EvaluationArtifactType, TrialIdentity | None, str, str]] = (
            expected_trial_artifact_descriptions | expected_run_artifact_descriptions
        )

        # Act
        await domain_facade.run_evaluation(evaluation_request, artifact_recorder.record_evaluation_artifact)

        # Assert
        actual_artifact_descriptions: set[tuple[EvaluationArtifactType, TrialIdentity | None, str, str]] = {
            (
                evaluation_artifact.artifact_type,
                evaluation_artifact.trial_identity,
                evaluation_artifact.filename_suffix,
                evaluation_artifact.content_type,
            )
            for evaluation_artifact in artifact_recorder.evaluation_artifacts
        }
        assert actual_artifact_descriptions == expected_artifact_descriptions, (
            f"missing {expected_artifact_descriptions - actual_artifact_descriptions}, "
            f"unexpected {actual_artifact_descriptions - expected_artifact_descriptions}"
        )

    async def test_RunEvaluation_WhenAnAnswerContainsUnicodeLineSeparators_ThenTheTrialCompletesAndItsAnswerKeepsThem(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        # The CLI writes these unescaped inside a JSON string; only "\n" ends an event line.
        answer_text: str = f"{RandomDataGenerator.create_random_sentence()}\u2028{RandomDataGenerator.create_random_sentence()}\u0085"
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions((CANDIDATE_PROMPT_MARKER,), create_trial_session(answer_text))
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        evaluation_request: EvaluationRequest = create_evaluation_request(sample_eval_suite, repetitions=1, variant_names=(CANDIDATE_VARIANT_NAME,))
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        artifact_recorder: ArtifactRecorder = ArtifactRecorder()
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(
            passes_gate=True,
            expected_scorecard_rows=tuple(create_expected_rows_for_every_check(CANDIDATE_VARIANT_NAME, trial_count=1, passed_count=1)),
        )
        expected_answer_contents: tuple[bytes, ...] = (answer_text.encode("utf-8"),)

        # Act
        actual_scorecard: Scorecard = await domain_facade.run_evaluation(evaluation_request, artifact_recorder.record_evaluation_artifact)

        # Assert
        actual_answer_contents: tuple[bytes, ...] = tuple(
            evaluation_artifact.content
            for evaluation_artifact in artifact_recorder.evaluation_artifacts
            if evaluation_artifact.artifact_type == EvaluationArtifactType.TRIAL_ANSWER
        )
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)
        assert actual_answer_contents == expected_answer_contents, (
            f"answer artifacts: expected {expected_answer_contents!r}, actual {actual_answer_contents!r}"
        )


@pytest.mark.acceptance
class TestRunEvaluationGradingOutcomes:
    async def test_RunEvaluation_WhenGatedVariantReportsAWrongAmount_ThenItsAmountCheckFailsWithTheReportedValueAndTheGateFails(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        wrong_total_amount: str = "1.23"
        baseline_answer_text: str = f"Baseline answer {RandomDataGenerator.create_random_word()}."
        candidate_answer_text: str = f"Candidate answer {RandomDataGenerator.create_random_word()}."
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions((BASELINE_PROMPT_MARKER,), create_trial_session(baseline_answer_text))
        test_mediator_coding_assistant_cli.script_sessions((CANDIDATE_PROMPT_MARKER,), create_trial_session(candidate_answer_text))
        test_mediator_coding_assistant_cli.script_sessions(
            (FACT_EXTRACTION_PROMPT_HEADING, candidate_answer_text), create_extraction_session(wrong_total_amount, "over")
        )
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        evaluation_request: EvaluationRequest = create_evaluation_request(sample_eval_suite, repetitions=1)
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        expected_candidate_rows: list[ExpectedScorecardRow] = create_expected_rows_for_every_check(
            CANDIDATE_VARIANT_NAME, trial_count=1, passed_count=1
        )
        expected_candidate_rows[0] = ExpectedScorecardRow(
            check_name=TOTAL_AMOUNT_CHECK_NAME,
            variant_name=CANDIDATE_VARIANT_NAME,
            trial_count=1,
            passed_count=0,
            errored_count=0,
            meets_minimum_pass_rate=False,
            failure_reason_phrases=(f"reported {wrong_total_amount}", f"expected {sample_eval_suite.expected_total_amount}"),
        )
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(
            passes_gate=False,
            expected_scorecard_rows=interleave_rows_by_check(
                create_expected_rows_for_every_check(BASELINE_VARIANT_NAME, trial_count=1, passed_count=1),
                expected_candidate_rows,
            ),
        )

        # Act
        actual_scorecard: Scorecard = await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)

    async def test_RunEvaluation_WhenOnlyTheUngatedVariantFailsChecks_ThenTheGateStillPasses(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        baseline_answer_text: str = f"Baseline answer {RandomDataGenerator.create_random_sentence()}"
        candidate_answer_text: str = f"Candidate answer {RandomDataGenerator.create_random_sentence()}"
        test_mediator_coding_assistant_cli.script_sessions((BASELINE_PROMPT_MARKER,), create_trial_session(baseline_answer_text, ran_python=False))
        test_mediator_coding_assistant_cli.script_sessions((CANDIDATE_PROMPT_MARKER,), create_trial_session(candidate_answer_text))
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        evaluation_request: EvaluationRequest = create_evaluation_request(sample_eval_suite, repetitions=1)
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        expected_baseline_rows: list[ExpectedScorecardRow] = create_expected_rows_for_every_check(
            BASELINE_VARIANT_NAME, trial_count=1, passed_count=1
        )
        expected_baseline_rows[2] = ExpectedScorecardRow(
            check_name=CODE_EXECUTED_CHECK_NAME,
            variant_name=BASELINE_VARIANT_NAME,
            trial_count=1,
            passed_count=0,
            errored_count=0,
            meets_minimum_pass_rate=False,
            failure_reason_phrases=("0 successful of 0 shell calls",),
        )
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(
            passes_gate=True,
            expected_scorecard_rows=interleave_rows_by_check(
                expected_baseline_rows,
                create_expected_rows_for_every_check(CANDIDATE_VARIANT_NAME, trial_count=1, passed_count=1),
            ),
        )

        # Act
        actual_scorecard: Scorecard = await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)

    async def test_RunEvaluation_WhenOnlyAnUngatedVariantIsRun_ThenTheGateDoesNotPass(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        baseline_answer_text: str = f"Baseline answer {RandomDataGenerator.create_random_sentence()}"
        test_mediator_coding_assistant_cli.script_sessions((BASELINE_PROMPT_MARKER,), create_trial_session(baseline_answer_text))
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        evaluation_request: EvaluationRequest = create_evaluation_request(sample_eval_suite, repetitions=1, variant_names=(BASELINE_VARIANT_NAME,))
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(
            passes_gate=False,
            expected_scorecard_rows=tuple(create_expected_rows_for_every_check(BASELINE_VARIANT_NAME, trial_count=1, passed_count=1)),
        )
        expected_gate_line: str = "Gate: **NOT EVALUATED (no gated variant was run)**"

        # Act
        actual_scorecard: Scorecard = await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)
        assert expected_gate_line in domain_facade.render_scorecard_report(actual_scorecard)

    async def test_RunEvaluation_WhenTheJudgeRejectsAnAnswer_ThenTheJudgeCheckFailsWithTheJudgesReason(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        judge_reason: str = f"The answer leads with conclusions ({RandomDataGenerator.create_random_word()})."
        candidate_answer_text: str = f"Candidate answer {RandomDataGenerator.create_random_sentence()}"
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions((CANDIDATE_PROMPT_MARKER,), create_trial_session(candidate_answer_text))
        test_mediator_coding_assistant_cli.script_sessions(
            (JUDGMENT_PROMPT_HEADING, sample_eval_suite.rubric_marker), create_judge_session(is_passed=False, reason=judge_reason)
        )
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        evaluation_request: EvaluationRequest = create_evaluation_request(sample_eval_suite, repetitions=1, variant_names=(CANDIDATE_VARIANT_NAME,))
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        expected_candidate_rows: list[ExpectedScorecardRow] = create_expected_rows_for_every_check(
            CANDIDATE_VARIANT_NAME, trial_count=1, passed_count=1
        )
        expected_candidate_rows[3] = ExpectedScorecardRow(
            check_name=TABLES_FIRST_CHECK_NAME,
            variant_name=CANDIDATE_VARIANT_NAME,
            trial_count=1,
            passed_count=0,
            errored_count=0,
            meets_minimum_pass_rate=False,
            failure_reason_phrases=(judge_reason,),
        )
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(passes_gate=False, expected_scorecard_rows=tuple(expected_candidate_rows))

        # Act
        actual_scorecard: Scorecard = await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)

    async def test_RunEvaluation_WhenAShellCommandRunsPythonAfterAHeredocNewline_ThenTheCodeExecutedCheckPasses(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        # The newline before "python" travels JSON-encoded on the wire; the check must see the command as typed.
        heredoc_shell_command: str = "cat > an.py <<'EOF'\nprint(1)\nEOF\npython an.py"
        candidate_answer_text: str = f"Candidate answer {RandomDataGenerator.create_random_sentence()}"
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions(
            (CANDIDATE_PROMPT_MARKER,), create_trial_session(candidate_answer_text, shell_command=heredoc_shell_command)
        )
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        evaluation_request: EvaluationRequest = create_evaluation_request(sample_eval_suite, repetitions=1, variant_names=(CANDIDATE_VARIANT_NAME,))
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(
            passes_gate=True,
            expected_scorecard_rows=tuple(create_expected_rows_for_every_check(CANDIDATE_VARIANT_NAME, trial_count=1, passed_count=1)),
        )

        # Act
        actual_scorecard: Scorecard = await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)


@pytest.mark.acceptance
class TestRunEvaluationFailurePaths:
    async def test_RunEvaluation_WhenATrialTimesOut_ThenThatTrialIsRecordedAsErroredForEveryCheckAndTheOtherTrialsStillCount(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        surviving_answer_text: str = f"Candidate answer {RandomDataGenerator.create_random_sentence()}"
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions(
            (CANDIDATE_PROMPT_MARKER,),
            ScriptedFailedStartSession(raised_exception=TimeoutError()),
            create_trial_session(surviving_answer_text),
        )
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        evaluation_request: EvaluationRequest = create_evaluation_request(sample_eval_suite, repetitions=2, variant_names=(CANDIDATE_VARIANT_NAME,))
        override_by_environment_variable_name: dict[str, str] = create_override_by_environment_variable_name(create_random_grader_model_name())
        override_by_environment_variable_name["PROMPT_EVALS_MAXIMUM_CONCURRENT_TRIALS"] = "1"
        domain_facade: DomainFacade = create_domain_facade(test_mediator_coding_assistant_cli, override_by_environment_variable_name)
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(
            passes_gate=False,
            expected_scorecard_rows=tuple(
                ExpectedScorecardRow(
                    check_name=expected_row.check_name,
                    variant_name=CANDIDATE_VARIANT_NAME,
                    trial_count=2,
                    passed_count=1,
                    errored_count=1,
                    meets_minimum_pass_rate=False,
                    failure_reason_phrases=("run-01: [errored]", f"did not finish within {SESSION_TIMEOUT_SECONDS} seconds"),
                )
                for expected_row in create_expected_rows_for_every_check(CANDIDATE_VARIANT_NAME, trial_count=2, passed_count=1)
            ),
        )

        # Act
        actual_scorecard: Scorecard = await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)

    async def test_RunEvaluation_WhenTheCliPrintsSomethingOtherThanAnEventStream_ThenTheTrialIsRecordedAsErrored(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions(
            (CANDIDATE_PROMPT_MARKER,), ScriptedRawOutputSession(raw_standard_output_text="this is not json\n")
        )
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        evaluation_request: EvaluationRequest = create_evaluation_request(sample_eval_suite, repetitions=1, variant_names=(CANDIDATE_VARIANT_NAME,))
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(
            passes_gate=False,
            expected_scorecard_rows=tuple(
                ExpectedScorecardRow(
                    check_name=check_name,
                    variant_name=CANDIDATE_VARIANT_NAME,
                    trial_count=1,
                    passed_count=0,
                    errored_count=1,
                    meets_minimum_pass_rate=False,
                    failure_reason_phrases=("could not be read", "a line is not JSON"),
                )
                for check_name in CHECK_NAMES_IN_SUITE_ORDER
            ),
        )

        # Act
        actual_scorecard: Scorecard = await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)

    async def test_RunEvaluation_WhenFactExtractionReturnsNoStructuredOutputTwice_ThenOnlyTheFactChecksAreErrored(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        candidate_answer_text: str = f"Candidate answer {RandomDataGenerator.create_random_sentence()}"
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions((CANDIDATE_PROMPT_MARKER,), create_trial_session(candidate_answer_text))
        test_mediator_coding_assistant_cli.script_sessions((FACT_EXTRACTION_PROMPT_HEADING,), ScriptedEventStreamSession(structured_output=None))
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        evaluation_request: EvaluationRequest = create_evaluation_request(sample_eval_suite, repetitions=1, variant_names=(CANDIDATE_VARIANT_NAME,))
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        expected_errored_fact_rows: list[ExpectedScorecardRow] = [
            ExpectedScorecardRow(
                check_name=check_name,
                variant_name=CANDIDATE_VARIANT_NAME,
                trial_count=1,
                passed_count=0,
                errored_count=1,
                meets_minimum_pass_rate=False,
                failure_reason_phrases=("fact extraction failed", "no structured output"),
            )
            for check_name in (TOTAL_AMOUNT_CHECK_NAME, STATUS_VALUE_CHECK_NAME)
        ]
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(
            passes_gate=False,
            expected_scorecard_rows=(
                *expected_errored_fact_rows,
                *create_expected_rows_for_every_check(CANDIDATE_VARIANT_NAME, trial_count=1, passed_count=1)[2:],
            ),
        )
        expected_extraction_attempt_count: int = 2

        # Act
        actual_scorecard: Scorecard = await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        actual_extraction_attempt_count: int = sum(
            1
            for captured_claude_invocation in test_mediator_coding_assistant_cli.captured_claude_invocations
            if captured_claude_invocation.prompt_text.startswith(FACT_EXTRACTION_PROMPT_HEADING)
        )
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)
        assert actual_extraction_attempt_count == expected_extraction_attempt_count

    async def test_RunEvaluation_WhenTheCliExitsNonZeroAfterReportingAnErrorResult_ThenTheTrialIsErroredWithThatResult(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        error_result_text: str = f"API Error: {RandomDataGenerator.create_random_sentence()}"
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions(
            (CANDIDATE_PROMPT_MARKER,), ScriptedEventStreamSession(final_text=error_result_text, is_error=True, exit_code=1)
        )
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        evaluation_request: EvaluationRequest = create_evaluation_request(sample_eval_suite, repetitions=1, variant_names=(CANDIDATE_VARIANT_NAME,))
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(
            passes_gate=False,
            expected_scorecard_rows=tuple(
                ExpectedScorecardRow(
                    check_name=check_name,
                    variant_name=CANDIDATE_VARIANT_NAME,
                    trial_count=1,
                    passed_count=0,
                    errored_count=1,
                    meets_minimum_pass_rate=False,
                    failure_reason_phrases=("ended in error", error_result_text),
                )
                for check_name in CHECK_NAMES_IN_SUITE_ORDER
            ),
        )

        # Act
        actual_scorecard: Scorecard = await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)

    async def test_RunEvaluation_WhenTheResultHasAnErrorSubtypeWithoutTheErrorFlag_ThenTheTrialIsErroredWithTheListedErrors(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        error_result_subtype: str = f"error_{RandomDataGenerator.create_random_word()}"
        error_message: str = RandomDataGenerator.create_random_sentence()
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions(
            (CANDIDATE_PROMPT_MARKER,), ScriptedEventStreamSession(result_subtype=error_result_subtype, error_messages=(error_message,))
        )
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        evaluation_request: EvaluationRequest = create_evaluation_request(sample_eval_suite, repetitions=1, variant_names=(CANDIDATE_VARIANT_NAME,))
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(
            passes_gate=False,
            expected_scorecard_rows=tuple(
                ExpectedScorecardRow(
                    check_name=check_name,
                    variant_name=CANDIDATE_VARIANT_NAME,
                    trial_count=1,
                    passed_count=0,
                    errored_count=1,
                    meets_minimum_pass_rate=False,
                    failure_reason_phrases=("ended in error", error_result_subtype, error_message),
                )
                for check_name in CHECK_NAMES_IN_SUITE_ORDER
            ),
        )

        # Act
        actual_scorecard: Scorecard = await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)

    @pytest.mark.parametrize("start_error", [FileNotFoundError(), PermissionError()], ids=["missing", "not-executable"])
    async def test_RunEvaluation_WhenTheClaudeCliCannotBeStarted_ThenClaudeCliStartFailedExceptionStopsTheEvaluation(
        self, tmp_path: Path, start_error: OSError
    ) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions((CANDIDATE_PROMPT_MARKER,), ScriptedFailedStartSession(raised_exception=start_error))
        evaluation_request: EvaluationRequest = create_evaluation_request(sample_eval_suite, repetitions=1, variant_names=(CANDIDATE_VARIANT_NAME,))
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        expected_message_phrases: tuple[str, ...] = ("could not be started", CLAUDE_EXECUTABLE_VARIABLE)
        expected_contextual_entries_by_name: dict[str, object] = {
            "AssistantName": CLAUDE_CODE_ASSISTANT_NAME,
            "ExecutablePath": "claude",
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
            actual_exception=exception_info.value,
        )

    async def test_RunEvaluation_WhenTheHostCannotPersistAnArtifact_ThenArtifactCallbackExceptionNamesTheArtifact(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        candidate_answer_text: str = f"Candidate answer {RandomDataGenerator.create_random_sentence()}"
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions((CANDIDATE_PROMPT_MARKER,), create_trial_session(candidate_answer_text))
        evaluation_request: EvaluationRequest = create_evaluation_request(sample_eval_suite, repetitions=1, variant_names=(CANDIDATE_VARIANT_NAME,))
        domain_facade: DomainFacade = create_domain_facade(
            test_mediator_coding_assistant_cli, create_override_by_environment_variable_name(create_random_grader_model_name())
        )

        def fail_to_persist(evaluation_artifact: EvaluationArtifact) -> None:
            raise OSError(f"disk full while writing {evaluation_artifact.filename_suffix}")

        expected_artifact_origin: str = f"trial {CANDIDATE_VARIANT_NAME} / {CASE_NAME} / run 1"
        expected_filename_suffix: str = "event_stream.jsonl"
        expected_message_phrases: tuple[str, ...] = (
            EvaluationArtifactType.TRIAL_EVENT_STREAM.value,
            expected_filename_suffix,
            expected_artifact_origin,
        )
        expected_contextual_entries_by_name: dict[str, object] = {
            "ArtifactType": EvaluationArtifactType.TRIAL_EVENT_STREAM.value,
            "FilenameSuffix": expected_filename_suffix,
            "ArtifactOrigin": expected_artifact_origin,
        }

        # Act
        with pytest.raises(ArtifactCallbackException) as exception_info:
            await domain_facade.run_evaluation(evaluation_request, fail_to_persist)

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=ArtifactCallbackException,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_exception=exception_info.value,
        )


@pytest.mark.acceptance
class TestRunEvaluationInvalidInput:
    async def test_RunEvaluation_WhenTheRequestHasSeveralProblemsOrAnUndefinedVariant_ThenEveryProblemIsReported(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        undefined_variant_name: str = f"variant-{RandomDataGenerator.create_random_word()}"
        domain_facade: DomainFacade = create_domain_facade(
            TestMediatorCodingAssistantCli(), create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        invalid_evaluation_request: EvaluationRequest = EvaluationRequest(
            coding_assistant=CodingAssistant.CLAUDE_CODE,
            eval_suite_directory=sample_eval_suite.eval_suite_directory,
            model_name="  ",
            effort_level=EffortLevel.MEDIUM,
            repetitions=0,
            variant_names=(CANDIDATE_VARIANT_NAME, CANDIDATE_VARIANT_NAME),
        )
        unknown_variant_evaluation_request: EvaluationRequest = create_evaluation_request(
            sample_eval_suite, repetitions=1, variant_names=(undefined_variant_name,)
        )
        expected_invalid_request_message_phrases: tuple[str, ...] = (
            "repetitions must be at least 1 (was 0)",
            "model_name must not be empty",
            f"variant '{CANDIDATE_VARIANT_NAME}' is requested 2 times",
        )
        expected_invalid_request_contextual_entries_by_name: dict[str, object] = {VALIDATION_PROBLEM_COUNT_ENTRY_NAME: 3}
        expected_unknown_variant_message_phrases: tuple[str, ...] = (
            f"variant '{undefined_variant_name}' is not defined",
            f"{BASELINE_VARIANT_NAME}, {CANDIDATE_VARIANT_NAME}",
        )
        expected_unknown_variant_contextual_entries_by_name: dict[str, object] = {VALIDATION_PROBLEM_COUNT_ENTRY_NAME: 1}

        # Act
        with pytest.raises(EvaluationRequestValidationException) as invalid_request_exception_info:
            await domain_facade.run_evaluation(invalid_evaluation_request, ArtifactRecorder().record_evaluation_artifact)
        with pytest.raises(EvaluationRequestValidationException) as unknown_variant_exception_info:
            await domain_facade.run_evaluation(unknown_variant_evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=EvaluationRequestValidationException,
            expected_message_phrases=expected_invalid_request_message_phrases,
            expected_contextual_entries_by_name=expected_invalid_request_contextual_entries_by_name,
            actual_exception=invalid_request_exception_info.value,
        )
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=EvaluationRequestValidationException,
            expected_message_phrases=expected_unknown_variant_message_phrases,
            expected_contextual_entries_by_name=expected_unknown_variant_contextual_entries_by_name,
            actual_exception=unknown_variant_exception_info.value,
        )

    async def test_RunEvaluation_WhenTheSuiteDirectoryHasNoSuiteDefinition_ThenEvalSuiteNotFoundExceptionIsRaised(self, tmp_path: Path) -> None:
        # Arrange
        domain_facade: DomainFacade = create_domain_facade(
            TestMediatorCodingAssistantCli(), create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        evaluation_request: EvaluationRequest = EvaluationRequest(
            coding_assistant=CodingAssistant.CLAUDE_CODE,
            eval_suite_directory=tmp_path,
            model_name=f"model-{RandomDataGenerator.create_random_word()}",
            effort_level=EffortLevel.LOW,
            repetitions=1,
        )
        expected_message_phrases: tuple[str, ...] = ("No eval suite definition was found", EVAL_SUITE_DEFINITION_FILE_NAME)
        expected_contextual_entries_by_name: dict[str, object] = {"EvalSuiteDefinitionPath": str(tmp_path / EVAL_SUITE_DEFINITION_FILE_NAME)}

        # Act
        with pytest.raises(EvalSuiteNotFoundException) as exception_info:
            await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=EvalSuiteNotFoundException,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_exception=exception_info.value,
        )

    async def test_RunEvaluation_WhenTheSuiteReferencesUndefinedNames_ThenEveryReferenceProblemIsReportedTogether(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        eval_suite_definition: dict[str, object] = SampleEvalSuiteBuilder.create_eval_suite_definition()
        missing_variant_name: str = f"variant-{RandomDataGenerator.create_random_word()}"
        undefined_fact_name: str = f"fact_{RandomDataGenerator.create_random_word()}"
        undefined_fact_check_name: str = f"check-{RandomDataGenerator.create_random_word()}"
        eval_suite_definition["gated_variant_names"] = [missing_variant_name]
        eval_suite_definition["checks"] = [
            {
                "check_name": undefined_fact_check_name,
                "grader": "amount",
                "fact_name": undefined_fact_name,
                "minimum_pass_rate": 0.5,
                "description": RandomDataGenerator.create_random_sentence(),
            },
        ]
        SampleEvalSuiteBuilder.write_eval_suite_definition(sample_eval_suite.eval_suite_directory, eval_suite_definition)
        domain_facade: DomainFacade = create_domain_facade(
            TestMediatorCodingAssistantCli(), create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        evaluation_request: EvaluationRequest = create_evaluation_request(sample_eval_suite, repetitions=1)
        expected_message_phrases: tuple[str, ...] = (
            f"gated variant '{missing_variant_name}' is not a defined prompt variant",
            f"fact '{undefined_fact_name}', which the fact extraction schema does not define",
            f"fact '{undefined_fact_name}', which case '{CASE_NAME}' has no expected value for",
        )
        expected_contextual_entries_by_name: dict[str, object] = {"DefinitionProblemCount": 3}

        # Act
        with pytest.raises(EvalSuiteDefinitionInvalidException) as exception_info:
            await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=EvalSuiteDefinitionInvalidException,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_exception=exception_info.value,
        )

    async def test_RunEvaluation_WhenACheckHasAnOutOfRangeMinimumPassRate_ThenEvalSuiteDefinitionInvalidExceptionNamesTheCheck(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        eval_suite_definition: dict[str, object] = SampleEvalSuiteBuilder.create_eval_suite_definition()
        out_of_range_check_name: str = f"check-{RandomDataGenerator.create_random_word()}"
        eval_suite_definition["checks"] = [
            {
                "check_name": out_of_range_check_name,
                "grader": "judge",
                "rubric_file": TABLES_FIRST_RUBRIC_FILE,
                "minimum_pass_rate": 2,
                "description": RandomDataGenerator.create_random_sentence(),
            },
        ]
        SampleEvalSuiteBuilder.write_eval_suite_definition(sample_eval_suite.eval_suite_directory, eval_suite_definition)
        domain_facade: DomainFacade = create_domain_facade(
            TestMediatorCodingAssistantCli(), create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        evaluation_request: EvaluationRequest = create_evaluation_request(sample_eval_suite, repetitions=1)
        expected_message_phrases: tuple[str, ...] = (f"check '{out_of_range_check_name}' needs a minimum_pass_rate between 0 and 1",)
        expected_contextual_entries_by_name: dict[str, object] = {"DefinitionProblemCount": 1}

        # Act
        with pytest.raises(EvalSuiteDefinitionInvalidException) as exception_info:
            await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=EvalSuiteDefinitionInvalidException,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_exception=exception_info.value,
        )

    async def test_RunEvaluation_WhenSuiteNamesAreUnsafeOrCollideAndAmountsAreNotNumbers_ThenEveryProblemIsReportedTogether(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        eval_suite_definition: dict[str, object] = SampleEvalSuiteBuilder.create_eval_suite_definition()
        unsafe_variant_name: str = "../escape"
        trailing_period_variant_name: str = "refund."
        non_numeric_amount: str = "$12.50"
        eval_suite_definition["prompt_variants"] = [
            {"variant_name": unsafe_variant_name, "prompt_file": BASELINE_PROMPT_FILE},
            {"variant_name": trailing_period_variant_name, "prompt_file": BASELINE_PROMPT_FILE},
            {"variant_name": CANDIDATE_VARIANT_NAME.capitalize(), "prompt_file": CANDIDATE_PROMPT_FILE},
            {"variant_name": CANDIDATE_VARIANT_NAME, "prompt_file": CANDIDATE_PROMPT_FILE},
        ]
        eval_suite_definition["gated_variant_names"] = []
        SampleEvalSuiteBuilder.write_eval_suite_definition(sample_eval_suite.eval_suite_directory, eval_suite_definition)
        SampleEvalSuiteBuilder.write_expected_facts(
            sample_eval_suite.eval_suite_directory, {TOTAL_FACT_NAME: [non_numeric_amount], STATUS_FACT_NAME: ["over"]}
        )
        domain_facade: DomainFacade = create_domain_facade(
            TestMediatorCodingAssistantCli(), create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        evaluation_request: EvaluationRequest = create_evaluation_request(sample_eval_suite, repetitions=1)
        expected_message_phrases: tuple[str, ...] = (
            f"variant name '{CANDIDATE_VARIANT_NAME}' is used 2 times",
            f"variant name '{unsafe_variant_name}' may contain only",
            f"variant name '{trailing_period_variant_name}' may contain only",
            "gated_variant_names must name at least one variant",
            f"accepts '{non_numeric_amount}' for '{TOTAL_FACT_NAME}'",
        )
        expected_contextual_entries_by_name: dict[str, object] = {"DefinitionProblemCount": 5}

        # Act
        with pytest.raises(EvalSuiteDefinitionInvalidException) as exception_info:
            await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=EvalSuiteDefinitionInvalidException,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_exception=exception_info.value,
        )

    async def test_RunEvaluation_WhenACheckNamesAnUnknownGrader_ThenOnlyTheUnknownGraderIsReported(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        eval_suite_definition: dict[str, object] = SampleEvalSuiteBuilder.create_eval_suite_definition()
        unknown_grader_check_name: str = f"check-{RandomDataGenerator.create_random_word()}"
        unknown_grader_name: str = "ammount"
        eval_suite_definition["checks"] = [
            {
                "check_name": unknown_grader_check_name,
                "grader": unknown_grader_name,
                "fact_name": TOTAL_FACT_NAME,
                "minimum_pass_rate": 0.5,
                "description": RandomDataGenerator.create_random_sentence(),
            },
        ]
        SampleEvalSuiteBuilder.write_eval_suite_definition(sample_eval_suite.eval_suite_directory, eval_suite_definition)
        domain_facade: DomainFacade = create_domain_facade(
            TestMediatorCodingAssistantCli(), create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        evaluation_request: EvaluationRequest = create_evaluation_request(sample_eval_suite, repetitions=1)
        expected_message_phrases: tuple[str, ...] = (f"check '{unknown_grader_check_name}' has unknown grader '{unknown_grader_name}'",)
        expected_contextual_entries_by_name: dict[str, object] = {"DefinitionProblemCount": 1}

        # Act
        with pytest.raises(EvalSuiteDefinitionInvalidException) as exception_info:
            await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=EvalSuiteDefinitionInvalidException,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_exception=exception_info.value,
        )

    async def test_RunEvaluation_WhenTheSuiteNamesToolsTheWayOneAssistantDoes_ThenEveryUnknownToolKindIsReported(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        assistant_specific_tool_name: str = "Bash"
        eval_suite_definition: dict[str, object] = SampleEvalSuiteBuilder.create_eval_suite_definition()
        eval_suite_definition["trial_tool_kinds"] = [assistant_specific_tool_name, "read_file"]
        eval_suite_definition["checks"] = [
            {
                "check_name": CODE_EXECUTED_CHECK_NAME,
                "grader": "tool_use",
                "tool_kind": assistant_specific_tool_name,
                "tool_input_pattern": "\\bpython",
                "minimum_pass_rate": 1.0,
                "description": RandomDataGenerator.create_random_sentence(),
            },
        ]
        SampleEvalSuiteBuilder.write_eval_suite_definition(sample_eval_suite.eval_suite_directory, eval_suite_definition)
        domain_facade: DomainFacade = create_domain_facade(
            TestMediatorCodingAssistantCli(), create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        evaluation_request: EvaluationRequest = create_evaluation_request(sample_eval_suite, repetitions=1)
        expected_message_phrases: tuple[str, ...] = (
            f"eval_suite.json has unknown tool kind '{assistant_specific_tool_name}'",
            f"check '{CODE_EXECUTED_CHECK_NAME}' has unknown tool kind '{assistant_specific_tool_name}'",
            "expected one of shell, read_file, write_file, edit_file, find_files, search_file_contents",
        )
        expected_contextual_entries_by_name: dict[str, object] = {"DefinitionProblemCount": 2}

        # Act
        with pytest.raises(EvalSuiteDefinitionInvalidException) as exception_info:
            await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=EvalSuiteDefinitionInvalidException,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_exception=exception_info.value,
        )

    async def test_RunEvaluation_WhenAnExpectedFactAcceptsOnlyBlankValues_ThenEvalSuiteDefinitionInvalidExceptionNamesTheFact(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        SampleEvalSuiteBuilder.write_expected_facts(
            sample_eval_suite.eval_suite_directory, {TOTAL_FACT_NAME: [sample_eval_suite.expected_total_amount], STATUS_FACT_NAME: ["  "]}
        )
        domain_facade: DomainFacade = create_domain_facade(
            TestMediatorCodingAssistantCli(), create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        evaluation_request: EvaluationRequest = create_evaluation_request(sample_eval_suite, repetitions=1)
        expected_message_phrases: tuple[str, ...] = (f"case '{CASE_NAME}' expects fact '{STATUS_FACT_NAME}' but accepts no non-blank value",)
        expected_contextual_entries_by_name: dict[str, object] = {"DefinitionProblemCount": 1}

        # Act
        with pytest.raises(EvalSuiteDefinitionInvalidException) as exception_info:
            await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=EvalSuiteDefinitionInvalidException,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_exception=exception_info.value,
        )

    async def test_RunEvaluation_WhenTheAnswerKeySitsInsideTheInputsDirectory_ThenEvalSuiteDefinitionInvalidExceptionSaysTheTrialCouldReadIt(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        answer_key_inside_inputs: str = f"{CASE_INPUTS_DIRECTORY}/{EXPECTED_FACTS_FILE_NAME}"
        (sample_eval_suite.eval_suite_directory / answer_key_inside_inputs).write_text(
            (sample_eval_suite.eval_suite_directory / CASE_EXPECTED_FACTS_FILE).read_text(encoding="utf-8"), encoding="utf-8"
        )
        eval_suite_definition: dict[str, object] = SampleEvalSuiteBuilder.create_eval_suite_definition()
        eval_suite_definition["cases"] = [
            {"case_name": CASE_NAME, "inputs_directory": CASE_INPUTS_DIRECTORY, "expected_facts_file": answer_key_inside_inputs},
        ]
        SampleEvalSuiteBuilder.write_eval_suite_definition(sample_eval_suite.eval_suite_directory, eval_suite_definition)
        domain_facade: DomainFacade = create_domain_facade(
            TestMediatorCodingAssistantCli(), create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        evaluation_request: EvaluationRequest = create_evaluation_request(sample_eval_suite, repetitions=1)
        expected_message_phrases: tuple[str, ...] = (
            f"the file '{answer_key_inside_inputs}' is inside the inputs directory of case '{CASE_NAME}', so the trial could read it",
        )
        expected_contextual_entries_by_name: dict[str, object] = {"DefinitionProblemCount": 1}

        # Act
        with pytest.raises(EvalSuiteDefinitionInvalidException) as exception_info:
            await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=EvalSuiteDefinitionInvalidException,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_exception=exception_info.value,
        )

    async def test_RunEvaluation_WhenAPromptFileIsNotUtf8_ThenEvalSuiteDefinitionInvalidExceptionNamesTheFile(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        # Windows PowerShell 5 `Out-File` writes UTF-16 by default.
        (sample_eval_suite.eval_suite_directory / BASELINE_PROMPT_FILE).write_text(sample_eval_suite.baseline_prompt_text, encoding="utf-16")
        domain_facade: DomainFacade = create_domain_facade(
            TestMediatorCodingAssistantCli(), create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        evaluation_request: EvaluationRequest = create_evaluation_request(sample_eval_suite, repetitions=1)
        expected_message_phrases: tuple[str, ...] = (f"the file '{BASELINE_PROMPT_FILE}' is not valid utf-8 text",)
        expected_contextual_entries_by_name: dict[str, object] = {"DefinitionProblemCount": 1}

        # Act
        with pytest.raises(EvalSuiteDefinitionInvalidException) as exception_info:
            await domain_facade.run_evaluation(evaluation_request, ArtifactRecorder().record_evaluation_artifact)

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=EvalSuiteDefinitionInvalidException,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_exception=exception_info.value,
        )


@pytest.mark.acceptance
class TestRenderScorecardReportInvalidInput:
    def test_RenderScorecardReport_WhenRowsAreOutOfLayoutOrRatesOutOfRange_ThenScorecardValidationExceptionReportsEveryProblem(self) -> None:
        # Arrange
        domain_facade: DomainFacade = create_domain_facade(
            TestMediatorCodingAssistantCli(), create_override_by_environment_variable_name(create_random_grader_model_name())
        )
        out_of_range_pass_rate: float = 1.5

        def create_scorecard_row(check_name: str, variant_name: str, pass_rate: float) -> ScorecardRow:
            return ScorecardRow(
                check_name=check_name,
                description=RandomDataGenerator.create_random_sentence(),
                variant_name=variant_name,
                trial_count=1,
                passed_count=1,
                errored_count=0,
                pass_rate=pass_rate,
                minimum_pass_rate=1.0,
                is_gated=variant_name == CANDIDATE_VARIANT_NAME,
                meets_minimum_pass_rate=True,
                failure_reasons=(),
            )

        scorecard: Scorecard = Scorecard(
            eval_suite_name=RandomDataGenerator.create_random_word(),
            coding_assistant=CodingAssistant.CLAUDE_CODE,
            model_name=f"model-{RandomDataGenerator.create_random_word()}",
            effort_level=EffortLevel.MEDIUM,
            repetitions=1,
            scorecard_rows=(
                create_scorecard_row(TOTAL_AMOUNT_CHECK_NAME, BASELINE_VARIANT_NAME, 1.0),
                create_scorecard_row(TOTAL_AMOUNT_CHECK_NAME, CANDIDATE_VARIANT_NAME, out_of_range_pass_rate),
                create_scorecard_row(STATUS_VALUE_CHECK_NAME, CANDIDATE_VARIANT_NAME, 1.0),
                create_scorecard_row(TOTAL_AMOUNT_CHECK_NAME, BASELINE_VARIANT_NAME, 1.0),
            ),
            failure_causes=(),
            passes_gate=True,
        )
        expected_message_phrases: tuple[str, ...] = (
            f"row '{TOTAL_AMOUNT_CHECK_NAME}' / '{CANDIDATE_VARIANT_NAME}' has a pass_rate of {out_of_range_pass_rate}",
            f"the rows of check '{TOTAL_AMOUNT_CHECK_NAME}' are not consecutive",
            f"check '{STATUS_VALUE_CHECK_NAME}' lists variants ['{CANDIDATE_VARIANT_NAME}']",
        )
        expected_contextual_entries_by_name: dict[str, object] = {VALIDATION_PROBLEM_COUNT_ENTRY_NAME: 4}

        # Act
        with pytest.raises(ScorecardValidationException) as exception_info:
            domain_facade.render_scorecard_report(scorecard)

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=ScorecardValidationException,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_exception=exception_info.value,
        )


@pytest.mark.acceptance
class TestDomainFacadeInvalidConfiguration:
    def test_DomainFacade_WhenAStringSettingIsSetToBlank_ThenConfigurationSettingExceptionNamesTheSetting(self) -> None:
        # Arrange
        blank_setting_value: str = "  "
        override_by_environment_variable_name: dict[str, str] = create_override_by_environment_variable_name(create_random_grader_model_name())
        override_by_environment_variable_name[GRADER_MODEL_VARIABLE] = blank_setting_value
        service_locator_testing: ServiceLocatorTesting = ServiceLocatorTesting(
            TestMediatorCodingAssistantCli(), override_by_environment_variable_name
        )
        expected_message_phrases: tuple[str, ...] = (GRADER_MODEL_VARIABLE, "expected a non-blank value")
        expected_contextual_entries_by_name: dict[str, object] = {
            "EnvironmentVariableName": GRADER_MODEL_VARIABLE,
            "ConfiguredValue": blank_setting_value,
        }

        # Act
        with pytest.raises(ConfigurationSettingException) as exception_info:
            DomainFacade(service_locator_testing)

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=ConfigurationSettingException,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_exception=exception_info.value,
        )
