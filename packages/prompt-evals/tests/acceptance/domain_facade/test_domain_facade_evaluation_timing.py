import json
import math
import secrets
from pathlib import Path
from typing import Final

import pytest
from acceptance_support.artifact_recorder import ArtifactRecorder
from acceptance_support.asserters.exception_asserter import ExceptionAsserter
from acceptance_support.claude_event_stream_builder import ClaudeEventStreamBuilder
from acceptance_support.codex_event_stream_builder import CodexEventStreamBuilder
from acceptance_support.random_data_generator import RandomDataGenerator
from acceptance_support.sample_eval_suite_builder import CANDIDATE_VARIANT_NAME, CASE_NAME, SampleEvalSuite, SampleEvalSuiteBuilder
from acceptance_support.scripted_cli_sessions import (
    ScriptedClaudeToolCall,
    ScriptedCodexCommandExecution,
    ScriptedEventStreamSession,
    ScriptedFailedStartSession,
)
from acceptance_support.scripted_grader_sessions import script_correct_grading
from acceptance_support.service_locator_testing import create_domain_facade
from acceptance_support.test_mediator_coding_assistant_cli import TestMediatorCodingAssistantCli

from prompt_evals import (
    CodingAssistant,
    DomainFacade,
    DurationSummary,
    EffortLevel,
    EvaluationArtifact,
    EvaluationArtifactType,
    EvaluationRequest,
    EvaluationRequestValidationException,
    RecordedCompletedTrial,
    RecordedTrial,
    RegradeRequest,
    Scorecard,
    ScorecardTiming,
    TrialIdentity,
    TrialTiming,
    VariantTiming,
)

CANDIDATE_PROMPT_MARKER: Final[str] = "Candidate prompt."
GRADER_MODEL_VARIABLE: Final[str] = "PROMPT_EVALS_GRADER_MODEL"
MILLISECONDS_PER_SECOND: Final[int] = 1000
VALIDATION_PROBLEM_COUNT_ENTRY_NAME: Final[str] = "ValidationProblemCount"


def create_domain_facade_for(test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli) -> DomainFacade:
    return create_domain_facade(test_mediator_coding_assistant_cli, {GRADER_MODEL_VARIABLE: f"grader-{RandomDataGenerator.create_random_word()}"})


def create_trial_identity(repetition_number: int) -> TrialIdentity:
    return TrialIdentity(variant_name=CANDIDATE_VARIANT_NAME, case_name=CASE_NAME, repetition_number=repetition_number)


def create_claude_session(duration_milliseconds: int = 1234) -> ScriptedEventStreamSession:
    return ScriptedEventStreamSession(
        final_text=f"Answer {RandomDataGenerator.create_random_sentence()}",
        scripted_tool_calls=(
            ScriptedClaudeToolCall(
                tool_name="Bash", tool_input={"command": "python totals.py"}, tool_result_text=RandomDataGenerator.create_random_word()
            ),
        ),
        duration_milliseconds=duration_milliseconds,
    )


def create_codex_event_stream() -> str:
    return CodexEventStreamBuilder.build_event_stream(
        ScriptedEventStreamSession(
            final_text=f"Answer {RandomDataGenerator.create_random_sentence()}",
            scripted_tool_calls=(
                ScriptedCodexCommandExecution(command="python totals.py", aggregated_output=RandomDataGenerator.create_random_word()),
            ),
        )
    )


def create_evaluation_request(sample_eval_suite: SampleEvalSuite, repetitions: int) -> EvaluationRequest:
    return EvaluationRequest(
        eval_suite_directory=sample_eval_suite.eval_suite_directory,
        coding_assistant=CodingAssistant.CLAUDE_CODE,
        model_name=f"model-{RandomDataGenerator.create_random_word()}",
        effort_level=EffortLevel.MEDIUM,
        repetitions=repetitions,
        variant_names=(CANDIDATE_VARIANT_NAME,),
    )


def create_regrade_request(
    sample_eval_suite: SampleEvalSuite, recorded_trials: tuple[RecordedTrial, ...], coding_assistant: CodingAssistant
) -> RegradeRequest:
    return RegradeRequest(
        eval_suite_directory=sample_eval_suite.eval_suite_directory,
        coding_assistant=coding_assistant,
        model_name=f"model-{RandomDataGenerator.create_random_word()}",
        effort_level=EffortLevel.MEDIUM,
        recorded_trials=recorded_trials,
    )


def create_random_seconds() -> float:
    return (secrets.randbelow(900_000) + 1_000) / 1000


def read_json_field(
    artifact_recorder: ArtifactRecorder, artifact_type: EvaluationArtifactType, trial_identity: TrialIdentity, field_name: str
) -> object:
    matching_artifacts: list[EvaluationArtifact] = [
        evaluation_artifact
        for evaluation_artifact in artifact_recorder.evaluation_artifacts
        if evaluation_artifact.artifact_type == artifact_type and evaluation_artifact.trial_identity == trial_identity
    ]
    assert len(matching_artifacts) == 1, f"expected one {artifact_type} artifact for {trial_identity}; actual {len(matching_artifacts)}"
    return json.loads(matching_artifacts[0].content.decode("utf-8"))[field_name]


def find_trial_timing_problems(trial_timing: TrialTiming) -> list[str]:
    trial_label: str = f"run {trial_timing.trial_identity.repetition_number}"
    if trial_timing.answer_duration_seconds is None or trial_timing.total_duration_seconds is None:
        return [f"{trial_label}: expected an answer time and a total time; actual {trial_timing}"]
    timing_problems: list[str] = []
    if trial_timing.answer_duration_seconds < 0 or trial_timing.grading_duration_seconds < 0:
        timing_problems.append(f"{trial_label}: expected times of zero seconds or more; actual {trial_timing}")
    if trial_timing.total_duration_seconds != trial_timing.answer_duration_seconds + trial_timing.grading_duration_seconds:
        timing_problems.append(f"{trial_label}: expected total time = answer time + grading time; actual {trial_timing}")
    return timing_problems


def find_saved_timing_problems(artifact_recorder: ArtifactRecorder, trial_timing: TrialTiming) -> list[str]:
    saved_durations: tuple[object, object] = (
        read_json_field(artifact_recorder, EvaluationArtifactType.TRIAL_TIMING, trial_timing.trial_identity, "answer_duration_seconds"),
        read_json_field(artifact_recorder, EvaluationArtifactType.TRIAL_GRADE, trial_timing.trial_identity, "grading_duration_seconds"),
    )
    scorecard_durations: tuple[object, object] = (trial_timing.answer_duration_seconds, trial_timing.grading_duration_seconds)
    if saved_durations == scorecard_durations:
        return []
    trial_label: str = f"run {trial_timing.trial_identity.repetition_number}"
    return [f"{trial_label}: timing.json and grade.json hold (answer, grading) {saved_durations}; the scorecard {scorecard_durations}"]


def describe_measured_trial_counts(variant_timing: VariantTiming) -> tuple[int, int | None, int | None, int | None]:
    return (
        variant_timing.trial_count,
        *(
            None if duration_summary is None else duration_summary.measured_trial_count
            for duration_summary in (
                variant_timing.answer_duration_summary,
                variant_timing.grading_duration_summary,
                variant_timing.total_duration_summary,
            )
        ),
    )


@pytest.mark.acceptance
class TestEvaluationTimingExpectedPaths:
    async def test_RunEvaluation_WhenEvaluationCompletes_ThenEveryRunHasAnAnswerTimeAGradingTimeAndTheirTotal(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions((CANDIDATE_PROMPT_MARKER,), create_claude_session())
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        artifact_recorder: ArtifactRecorder = ArtifactRecorder()
        expected_trial_identities: list[TrialIdentity] = [create_trial_identity(1), create_trial_identity(2)]
        expected_measured_trial_counts: tuple[int, int | None, int | None, int | None] = (2, 2, 2, 2)

        # Act
        actual_scorecard: Scorecard = await create_domain_facade_for(test_mediator_coding_assistant_cli).run_evaluation(
            create_evaluation_request(sample_eval_suite, repetitions=2), artifact_recorder.record_evaluation_artifact
        )

        # Assert
        actual_scorecard_timing: ScorecardTiming = actual_scorecard.scorecard_timing
        timing_problems: list[str] = [
            timing_problem
            for trial_timing in actual_scorecard_timing.trial_timings
            for timing_problem in (*find_trial_timing_problems(trial_timing), *find_saved_timing_problems(artifact_recorder, trial_timing))
        ]
        actual_trial_identities: list[TrialIdentity] = [trial_timing.trial_identity for trial_timing in actual_scorecard_timing.trial_timings]
        if actual_trial_identities != expected_trial_identities:
            timing_problems.append(f"trial timings: expected {expected_trial_identities}; actual {actual_trial_identities}")
        actual_measured_trial_counts: tuple[int, int | None, int | None, int | None] = describe_measured_trial_counts(
            actual_scorecard_timing.variant_timings[0]
        )
        if actual_measured_trial_counts != expected_measured_trial_counts:
            timing_problems.append(
                f"(runs, answer, grading and total times measured): expected {expected_measured_trial_counts}; actual {actual_measured_trial_counts}"
            )
        assert not timing_problems, f"{len(timing_problems)} timing problems:\n" + "\n".join(timing_problems)

    async def test_RunEvaluation_WhenATrialErrors_ThenItKeepsItsAnswerTimeButIsLeftOutOfTheTimeSummaries(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions((CANDIDATE_PROMPT_MARKER,), ScriptedFailedStartSession(raised_exception=TimeoutError()))
        expected_outcome: tuple[bool, float, list[str], tuple[int, int | None, int | None, int | None]] = (False, 0.0, [], (1, None, None, None))

        # Act
        actual_scorecard: Scorecard = await create_domain_facade_for(test_mediator_coding_assistant_cli).run_evaluation(
            create_evaluation_request(sample_eval_suite, repetitions=1), ArtifactRecorder().record_evaluation_artifact
        )

        # Assert
        actual_trial_timing: TrialTiming = actual_scorecard.scorecard_timing.trial_timings[0]
        actual_outcome: tuple[bool, float, list[str], tuple[int, int | None, int | None, int | None]] = (
            actual_trial_timing.session_answered,
            actual_trial_timing.grading_duration_seconds,
            find_trial_timing_problems(actual_trial_timing),
            describe_measured_trial_counts(actual_scorecard.scorecard_timing.variant_timings[0]),
        )
        assert actual_outcome == expected_outcome, (
            f"expected (session answered, grading time, trial timing problems, (runs, answer, grading and total times measured)) "
            f"{expected_outcome}; actual {actual_outcome}"
        )

    async def test_RegradeEvaluation_WhenARecordedTrialSavedAnAnswerTime_ThenTheScorecardReportsItAndItIsSavedAgain(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        trial_identity: TrialIdentity = create_trial_identity(1)
        expected_answer_duration_seconds: float = create_random_seconds()
        recorded_completed_trial: RecordedCompletedTrial = RecordedCompletedTrial(
            trial_identity=trial_identity,
            event_stream_text=ClaudeEventStreamBuilder.build_event_stream(
                f"model-{RandomDataGenerator.create_random_word()}", create_claude_session()
            ),
            answer_duration_seconds=expected_answer_duration_seconds,
        )
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        artifact_recorder: ArtifactRecorder = ArtifactRecorder()
        expected_outcome: tuple[object, object, list[str]] = (expected_answer_duration_seconds, expected_answer_duration_seconds, [])

        # Act
        actual_scorecard: Scorecard = await create_domain_facade_for(test_mediator_coding_assistant_cli).regrade_evaluation(
            create_regrade_request(sample_eval_suite, (recorded_completed_trial,), CodingAssistant.CLAUDE_CODE),
            artifact_recorder.record_evaluation_artifact,
        )

        # Assert
        actual_trial_timing: TrialTiming = actual_scorecard.scorecard_timing.trial_timings[0]
        actual_outcome: tuple[object, object, list[str]] = (
            actual_trial_timing.answer_duration_seconds,
            read_json_field(artifact_recorder, EvaluationArtifactType.TRIAL_TIMING, trial_identity, "answer_duration_seconds"),
            find_trial_timing_problems(actual_trial_timing),
        )
        assert actual_outcome == expected_outcome, (
            f"expected (answer time on the scorecard, answer time in timing.json, trial timing problems) {expected_outcome}; actual {actual_outcome}"
        )

    async def test_RegradeEvaluation_WhenAClaudeRecordingSavedNoAnswerTime_ThenTheDurationItsEventStreamReportsIsUsed(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        stream_duration_milliseconds: int = secrets.randbelow(900_000) + 1_000
        recorded_completed_trial: RecordedCompletedTrial = RecordedCompletedTrial(
            trial_identity=create_trial_identity(1),
            event_stream_text=ClaudeEventStreamBuilder.build_event_stream(
                f"model-{RandomDataGenerator.create_random_word()}", create_claude_session(stream_duration_milliseconds)
            ),
            answer_duration_seconds=None,
        )
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        expected_answer_duration_seconds: float = stream_duration_milliseconds / MILLISECONDS_PER_SECOND

        # Act
        actual_scorecard: Scorecard = await create_domain_facade_for(test_mediator_coding_assistant_cli).regrade_evaluation(
            create_regrade_request(sample_eval_suite, (recorded_completed_trial,), CodingAssistant.CLAUDE_CODE),
            ArtifactRecorder().record_evaluation_artifact,
        )

        # Assert
        actual_answer_duration_seconds: float | None = actual_scorecard.scorecard_timing.trial_timings[0].answer_duration_seconds
        assert actual_answer_duration_seconds == expected_answer_duration_seconds, (
            f"expected the stream's {expected_answer_duration_seconds}s; actual {actual_answer_duration_seconds}"
        )

    async def test_RegradeEvaluation_WhenACodexRecordingSavedNoAnswerTime_ThenItsAnswerAndTotalTimesAreNotRecorded(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        recorded_completed_trial: RecordedCompletedTrial = RecordedCompletedTrial(
            trial_identity=create_trial_identity(1), event_stream_text=create_codex_event_stream(), answer_duration_seconds=None
        )
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        script_correct_grading(test_mediator_coding_assistant_cli, sample_eval_suite)
        expected_recorded_times: tuple[bool, bool, bool] = (False, True, False)

        # Act
        actual_scorecard: Scorecard = await create_domain_facade_for(test_mediator_coding_assistant_cli).regrade_evaluation(
            create_regrade_request(sample_eval_suite, (recorded_completed_trial,), CodingAssistant.CODEX),
            ArtifactRecorder().record_evaluation_artifact,
        )

        # Assert
        actual_variant_timing: VariantTiming = actual_scorecard.scorecard_timing.variant_timings[0]
        actual_recorded_times: tuple[bool, bool, bool] = (
            actual_variant_timing.answer_duration_summary is not None,
            actual_variant_timing.grading_duration_summary is not None,
            actual_variant_timing.total_duration_summary is not None,
        )
        assert actual_recorded_times == expected_recorded_times, (
            f"expected (answer, grading, total) recorded {expected_recorded_times}; actual {actual_recorded_times}"
        )


@pytest.mark.acceptance
class TestEvaluationTimingInvalidInput:
    async def test_RegradeEvaluation_WhenARecordedAnswerTimeIsNotAFiniteNumberOfSeconds_ThenEvaluationRequestValidationExceptionNamesTheTrial(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        trial_identity: TrialIdentity = create_trial_identity(1)
        invalid_answer_duration_seconds: float = math.nan
        recorded_completed_trial: RecordedCompletedTrial = RecordedCompletedTrial(
            trial_identity=trial_identity,
            event_stream_text=ClaudeEventStreamBuilder.build_event_stream(
                f"model-{RandomDataGenerator.create_random_word()}", create_claude_session()
            ),
            answer_duration_seconds=invalid_answer_duration_seconds,
        )
        expected_message_phrases: tuple[str, ...] = (
            f"trial {trial_identity.variant_name} / {trial_identity.case_name} / run {trial_identity.repetition_number}",
            f"has a recorded answer time of {invalid_answer_duration_seconds}",
        )
        expected_contextual_entries_by_name: dict[str, object] = {VALIDATION_PROBLEM_COUNT_ENTRY_NAME: 1}

        # Act
        with pytest.raises(EvaluationRequestValidationException) as exception_info:
            await create_domain_facade_for(TestMediatorCodingAssistantCli()).regrade_evaluation(
                create_regrade_request(sample_eval_suite, (recorded_completed_trial,), CodingAssistant.CLAUDE_CODE),
                ArtifactRecorder().record_evaluation_artifact,
            )

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=EvaluationRequestValidationException,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_exception=exception_info.value,
        )


@pytest.mark.acceptance
class TestRenderScorecardReportTiming:
    def test_RenderScorecardReport_WhenVariantsHaveTimes_ThenTheTimePerRunTableShowsTheMedianAndRangeOfEachTime(self) -> None:
        # Arrange
        domain_facade: DomainFacade = create_domain_facade_for(TestMediatorCodingAssistantCli())
        scorecard: Scorecard = Scorecard(
            eval_suite_name=RandomDataGenerator.create_random_word(),
            coding_assistant=CodingAssistant.CODEX,
            model_name=f"model-{RandomDataGenerator.create_random_word()}",
            effort_level=EffortLevel.MEDIUM,
            repetitions=5,
            scorecard_rows=(),
            failure_causes=(),
            scorecard_timing=ScorecardTiming(
                variant_timings=(
                    VariantTiming(
                        variant_name=CANDIDATE_VARIANT_NAME,
                        is_gated=True,
                        trial_count=5,
                        answer_duration_summary=DurationSummary(
                            median_seconds=65.4, minimum_seconds=59.6, maximum_seconds=3725.0, measured_trial_count=3
                        ),
                        grading_duration_summary=DurationSummary(
                            median_seconds=8.44, minimum_seconds=0.0, maximum_seconds=12.0, measured_trial_count=5
                        ),
                        total_duration_summary=None,
                    ),
                ),
                trial_timings=(),
            ),
            passes_gate=False,
        )
        expected_timing_lines: tuple[str, ...] = (
            "| Variant | Runs | Answer time (model session) | Grading time (eval analysis) | Total time |",
            f"| {CANDIDATE_VARIANT_NAME} (gated) | 5 | 1m 05s (1m 00s to 1h 02m), 3 of 5 runs | 8.4s (0.0s to 12s) | not recorded |",
        )

        # Act
        actual_report: str = domain_facade.render_scorecard_report(scorecard)

        # Assert
        actual_report_lines: list[str] = actual_report.splitlines()
        missing_timing_lines: list[str] = [expected_line for expected_line in expected_timing_lines if expected_line not in actual_report_lines]
        assert not missing_timing_lines, f"expected the timing table lines {missing_timing_lines}; actual report:\n{actual_report}"
