import secrets
from pathlib import Path
from typing import Final

import pytest
from acceptance_support.artifact_recorder import ArtifactRecorder
from acceptance_support.asserters.exception_asserter import ExceptionAsserter
from acceptance_support.asserters.scorecard_asserter import ExpectedScorecard, ScorecardAsserter
from acceptance_support.claude_event_stream_builder import ClaudeEventStreamBuilder
from acceptance_support.codex_event_stream_builder import CodexEventStreamBuilder
from acceptance_support.expected_scorecard_rows import create_expected_rows_for_every_check, interleave_rows_by_check
from acceptance_support.random_data_generator import RandomDataGenerator
from acceptance_support.sample_eval_suite_builder import (
    BASELINE_VARIANT_NAME,
    CANDIDATE_VARIANT_NAME,
    CASE_NAME,
    SampleEvalSuite,
    SampleEvalSuiteBuilder,
)
from acceptance_support.scripted_cli_sessions import (
    ScriptedClaudeEventStreamSession,
    ScriptedClaudeToolCall,
    ScriptedCodexCommandExecution,
    ScriptedCodexEventStreamSession,
)
from acceptance_support.scripted_grader_sessions import (
    FACT_EXTRACTION_PROMPT_HEADING,
    JUDGMENT_PROMPT_HEADING,
    create_extraction_session,
    script_correct_grading,
)
from acceptance_support.service_locator_testing import create_domain_facade
from acceptance_support.test_mediator_coding_assistant_cli import TestMediatorCodingAssistantCli

from prompt_evals import (
    CodingAssistant,
    DomainFacade,
    EffortLevel,
    EvaluationArtifact,
    EvaluationArtifactType,
    RecordedCompletedTrial,
    RecordedErroredTrial,
    RecordedTrial,
    RegradeRequest,
    RegradeRequestTrialsNotInEvalSuiteException,
    RegradeRequestValidationException,
    Scorecard,
    TrialIdentity,
)

GRADER_MODEL_VARIABLE: Final[str] = "PROMPT_EVALS_GRADER_MODEL"
VALIDATION_PROBLEM_COUNT_ENTRY_NAME: Final[str] = "ValidationProblemCount"
GRADER_PROMPT_HEADINGS: Final[tuple[str, ...]] = (FACT_EXTRACTION_PROMPT_HEADING, JUDGMENT_PROMPT_HEADING)


def create_trial_identity(variant_name: str, repetition_number: int) -> TrialIdentity:
    return TrialIdentity(variant_name=variant_name, case_name=CASE_NAME, repetition_number=repetition_number)


def record_claude_trial(trial_identity: TrialIdentity, answer_text: str) -> RecordedCompletedTrial:
    # A recorded trial is the event stream the Claude Code CLI printed when the trial ran, here one that ran Python.
    return RecordedCompletedTrial(
        answer_duration_seconds=None,
        trial_identity=trial_identity,
        event_stream_text=ClaudeEventStreamBuilder.build_event_stream(
            f"model-{RandomDataGenerator.create_random_word()}",
            ScriptedClaudeEventStreamSession(
                final_text=answer_text,
                scripted_claude_tool_calls=(
                    ScriptedClaudeToolCall(
                        tool_name="Bash", tool_input={"command": "python totals.py"}, tool_result_text=RandomDataGenerator.create_random_word()
                    ),
                ),
            ),
        ),
    )


def create_regrade_request(
    sample_eval_suite: SampleEvalSuite, recorded_trials: tuple[RecordedTrial, ...], coding_assistant: CodingAssistant = CodingAssistant.CLAUDE_CODE
) -> RegradeRequest:
    return RegradeRequest(
        eval_suite_directory=sample_eval_suite.eval_suite_directory,
        coding_assistant=coding_assistant,
        model_name=f"model-{RandomDataGenerator.create_random_word()}",
        effort_level=EffortLevel.MEDIUM,
        recorded_trials=recorded_trials,
    )


def create_domain_facade_for(test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli) -> DomainFacade:
    return create_domain_facade(test_mediator_coding_assistant_cli, {GRADER_MODEL_VARIABLE: f"grader-{RandomDataGenerator.create_random_word()}"})


def create_answer_text() -> str:
    return f"Recorded answer {RandomDataGenerator.create_random_sentence()}"


@pytest.mark.acceptance
class TestRegradeEvaluationExpectedPaths:
    async def test_RegradeEvaluation_WhenRecordedTrialsAreRegraded_ThenOnlyGraderSessionsRunAndEveryCheckIsGraded(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        recorded_trials: tuple[RecordedTrial, ...] = tuple(
            record_claude_trial(create_trial_identity(variant_name, repetition_number), create_answer_text())
            for variant_name in (BASELINE_VARIANT_NAME, CANDIDATE_VARIANT_NAME)
            for repetition_number in (1, 2)
        )
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        regrade_request: RegradeRequest = create_regrade_request(sample_eval_suite, recorded_trials)
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(
            passes_gate=True,
            expected_scorecard_rows=interleave_rows_by_check(
                create_expected_rows_for_every_check(BASELINE_VARIANT_NAME, trial_count=2, passed_count=2),
                create_expected_rows_for_every_check(CANDIDATE_VARIANT_NAME, trial_count=2, passed_count=2),
            ),
        )
        expected_run_description: tuple[object, ...] = (regrade_request.coding_assistant, regrade_request.model_name, 2, 0)

        # Act
        actual_scorecard: Scorecard = await create_domain_facade_for(test_mediator_coding_assistant_cli).regrade_evaluation(
            regrade_request, ArtifactRecorder().record_evaluation_artifact
        )

        # Assert
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)
        actual_trial_session_count: int = sum(
            1
            for captured_cli_invocation in test_mediator_coding_assistant_cli.captured_cli_invocations
            if not captured_cli_invocation.prompt_text.startswith(GRADER_PROMPT_HEADINGS)
        )
        actual_run_description: tuple[object, ...] = (
            actual_scorecard.coding_assistant,
            actual_scorecard.model_name,
            actual_scorecard.repetitions,
            actual_trial_session_count,
        )
        assert actual_run_description == expected_run_description, (
            f"expected (assistant, model, repetitions, trial sessions) {expected_run_description}; actual {actual_run_description}"
        )

    async def test_RegradeEvaluation_WhenARecordedAnswerIsGraded_ThenTheGraderReadsThatAnswerAndItIsEmittedAgain(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        candidate_answer_text: str = create_answer_text()
        trial_identity: TrialIdentity = create_trial_identity(CANDIDATE_VARIANT_NAME, 1)
        wrong_total_amount: str = RandomDataGenerator.create_random_amount_text()
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions(
            (FACT_EXTRACTION_PROMPT_HEADING, candidate_answer_text), create_extraction_session(wrong_total_amount, "over")
        )
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        artifact_recorder: ArtifactRecorder = ArtifactRecorder()
        expected_outcome: tuple[object, ...] = (False, candidate_answer_text)

        # Act
        actual_scorecard: Scorecard = await create_domain_facade_for(test_mediator_coding_assistant_cli).regrade_evaluation(
            create_regrade_request(sample_eval_suite, (record_claude_trial(trial_identity, candidate_answer_text),)),
            artifact_recorder.record_evaluation_artifact,
        )

        # Assert
        answer_evaluation_artifacts: list[EvaluationArtifact] = [
            evaluation_artifact
            for evaluation_artifact in artifact_recorder.evaluation_artifacts
            if evaluation_artifact.artifact_type == EvaluationArtifactType.TRIAL_ANSWER and evaluation_artifact.trial_identity == trial_identity
        ]
        actual_outcome: tuple[object, ...] = (
            actual_scorecard.passes_gate,
            answer_evaluation_artifacts[0].content.decode("utf-8") if answer_evaluation_artifacts else None,
        )
        assert actual_outcome == expected_outcome, f"expected (gate, emitted answer) {expected_outcome}; actual {actual_outcome}"

    async def test_RegradeEvaluation_WhenRecordedTrialsRanInCodex_ThenTheirStreamsAreReadAsCodexSessions(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        recorded_trials: tuple[RecordedTrial, ...] = tuple(
            RecordedCompletedTrial(
                answer_duration_seconds=None,
                trial_identity=create_trial_identity(CANDIDATE_VARIANT_NAME, repetition_number),
                event_stream_text=CodexEventStreamBuilder.build_event_stream(
                    ScriptedCodexEventStreamSession(
                        final_text=create_answer_text(),
                        scripted_codex_tool_calls=(
                            ScriptedCodexCommandExecution(command="python totals.py", aggregated_output=RandomDataGenerator.create_random_sentence()),
                        ),
                    )
                ),
            )
            for repetition_number in (1, 2)
        )
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(
            passes_gate=True,
            expected_scorecard_rows=tuple(create_expected_rows_for_every_check(CANDIDATE_VARIANT_NAME, trial_count=2, passed_count=2)),
        )

        # Act
        actual_scorecard: Scorecard = await create_domain_facade_for(test_mediator_coding_assistant_cli).regrade_evaluation(
            create_regrade_request(sample_eval_suite, recorded_trials, CodingAssistant.CODEX), ArtifactRecorder().record_evaluation_artifact
        )

        # Assert
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)


@pytest.mark.acceptance
class TestRegradeEvaluationFailurePaths:
    async def test_RegradeEvaluation_WhenARecordedTrialErroredOrItsStreamIsUnreadable_ThenThoseTrialsAreErroredForEveryCheck(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        recorded_error_description: str = RandomDataGenerator.create_random_sentence()
        recorded_trials: tuple[RecordedTrial, ...] = (
            record_claude_trial(create_trial_identity(CANDIDATE_VARIANT_NAME, 1), create_answer_text()),
            RecordedErroredTrial(
                trial_identity=create_trial_identity(CANDIDATE_VARIANT_NAME, 2),
                error_description=recorded_error_description,
                answer_duration_seconds=None,
            ),
            RecordedCompletedTrial(
                trial_identity=create_trial_identity(CANDIDATE_VARIANT_NAME, 3),
                event_stream_text=RandomDataGenerator.create_random_sentence(),
                answer_duration_seconds=None,
            ),
        )
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(
            passes_gate=False,
            expected_scorecard_rows=tuple(
                create_expected_rows_for_every_check(CANDIDATE_VARIANT_NAME, trial_count=3, passed_count=1, errored_count=2)
            ),
        )

        # Act
        actual_scorecard: Scorecard = await create_domain_facade_for(test_mediator_coding_assistant_cli).regrade_evaluation(
            create_regrade_request(sample_eval_suite, recorded_trials), ArtifactRecorder().record_evaluation_artifact
        )

        # Assert
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)
        actual_failure_reasons: str = "\n".join(actual_scorecard.scorecard_rows[0].failure_reasons)
        assert recorded_error_description in actual_failure_reasons, (
            f"expected the recorded error {recorded_error_description!r} among the failure reasons; actual {actual_failure_reasons!r}"
        )


@pytest.mark.acceptance
class TestRegradeEvaluationInvalidInput:
    async def test_RegradeEvaluation_WhenTheModelIsBlankAndATrialIsRecordedTwice_ThenEveryProblemIsReported(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        repeated_trial_identity: TrialIdentity = create_trial_identity(CANDIDATE_VARIANT_NAME, secrets.randbelow(9) + 1)
        regrade_request: RegradeRequest = RegradeRequest(
            eval_suite_directory=sample_eval_suite.eval_suite_directory,
            coding_assistant=CodingAssistant.CLAUDE_CODE,
            model_name=" ",
            effort_level=EffortLevel.MEDIUM,
            recorded_trials=(
                record_claude_trial(repeated_trial_identity, create_answer_text()),
                record_claude_trial(repeated_trial_identity, create_answer_text()),
            ),
        )
        expected_message_phrases: tuple[str, ...] = (
            "model_name must not be empty",
            f"trial {CANDIDATE_VARIANT_NAME} / {CASE_NAME} / run {repeated_trial_identity.repetition_number} is recorded 2 times",
        )
        expected_contextual_entries_by_name: dict[str, object] = {VALIDATION_PROBLEM_COUNT_ENTRY_NAME: len(expected_message_phrases)}

        # Act
        with pytest.raises(RegradeRequestValidationException) as exception_info:
            await create_domain_facade_for(TestMediatorCodingAssistantCli()).regrade_evaluation(
                regrade_request, ArtifactRecorder().record_evaluation_artifact
            )

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=RegradeRequestValidationException,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_prompt_evals_base_exception=exception_info.value,
        )

    async def test_RegradeEvaluation_WhenNoTrialIsRecorded_ThenRegradeRequestValidationExceptionSaysSo(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        expected_message_phrases: tuple[str, ...] = ("there are no recorded trials to grade",)
        expected_contextual_entries_by_name: dict[str, object] = {VALIDATION_PROBLEM_COUNT_ENTRY_NAME: len(expected_message_phrases)}

        # Act
        with pytest.raises(RegradeRequestValidationException) as exception_info:
            await create_domain_facade_for(TestMediatorCodingAssistantCli()).regrade_evaluation(
                create_regrade_request(sample_eval_suite, ()), ArtifactRecorder().record_evaluation_artifact
            )

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=RegradeRequestValidationException,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_prompt_evals_base_exception=exception_info.value,
        )

    async def test_RegradeEvaluation_WhenRecordedTrialsNameAVariantAndCaseTheSuiteLacks_ThenEveryUndefinedNameIsReported(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        undefined_variant_name: str = f"variant-{RandomDataGenerator.create_random_word()}"
        undefined_case_name: str = f"case-{RandomDataGenerator.create_random_word()}"
        recorded_trials: tuple[RecordedTrial, ...] = (
            record_claude_trial(TrialIdentity(variant_name=undefined_variant_name, case_name=CASE_NAME, repetition_number=1), create_answer_text()),
            record_claude_trial(
                TrialIdentity(variant_name=CANDIDATE_VARIANT_NAME, case_name=undefined_case_name, repetition_number=1), create_answer_text()
            ),
        )
        # Each problem lists the names the suite does define, so the reader can see what the recorded trial should have used.
        expected_message_phrases: tuple[str, ...] = (
            (
                f"the recorded variant '{undefined_variant_name}' is not defined by suite '{sample_eval_suite.eval_suite_name}' "
                f"(defined variants: {BASELINE_VARIANT_NAME}, {CANDIDATE_VARIANT_NAME})"
            ),
            f"the recorded case '{undefined_case_name}' is not defined by suite '{sample_eval_suite.eval_suite_name}' (defined cases: {CASE_NAME})",
        )
        expected_contextual_entries_by_name: dict[str, object] = {VALIDATION_PROBLEM_COUNT_ENTRY_NAME: len(expected_message_phrases)}

        # Act
        with pytest.raises(RegradeRequestTrialsNotInEvalSuiteException) as exception_info:
            await create_domain_facade_for(TestMediatorCodingAssistantCli()).regrade_evaluation(
                create_regrade_request(sample_eval_suite, recorded_trials), ArtifactRecorder().record_evaluation_artifact
            )

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=RegradeRequestTrialsNotInEvalSuiteException,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_prompt_evals_base_exception=exception_info.value,
        )
