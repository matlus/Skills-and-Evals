import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Final, cast

import pytest
from acceptance_support.artifact_recorder import ArtifactRecorder
from acceptance_support.asserters.exception_asserter import ExceptionAsserter
from acceptance_support.asserters.failure_cause_asserter import ExpectedFailureCause, FailureCauseAsserter
from acceptance_support.asserters.scorecard_asserter import ExpectedScorecard, ExpectedScorecardRow, ScorecardAsserter
from acceptance_support.expected_scorecard_rows import create_expected_rows_for_every_check
from acceptance_support.random_data_generator import RandomDataGenerator
from acceptance_support.sample_eval_suite_builder import (
    CANDIDATE_VARIANT_NAME,
    TABLES_FIRST_CHECK_NAME,
    TOTAL_AMOUNT_CHECK_NAME,
    TOTAL_FACT_NAME,
    SampleEvalSuite,
    SampleEvalSuiteBuilder,
)
from acceptance_support.sample_reference_ledger_builder import (
    CASE_REFERENCE_LEDGER_FILE,
    SampleLedgerEntry,
    SampleReferenceLedger,
    SampleReferenceLedgerBuilder,
)
from acceptance_support.scripted_cli_sessions import ScriptedClaudeToolCall, ScriptedEventStreamSession
from acceptance_support.scripted_grader_sessions import (
    FACT_EXTRACTION_PROMPT_HEADING,
    JUDGMENT_PROMPT_HEADING,
    ScriptedDisputedAmount,
    create_extraction_session,
    create_judge_session,
)
from acceptance_support.service_locator_testing import create_domain_facade
from acceptance_support.test_mediator_coding_assistant_cli import TestMediatorCodingAssistantCli

from prompt_evals import (
    CodingAssistant,
    DomainFacade,
    EffortLevel,
    EvalSuiteDefinitionInvalidException,
    EvaluationArtifact,
    EvaluationArtifactType,
    EvaluationRequest,
    FailureCause,
    Scorecard,
)

CANDIDATE_PROMPT_MARKER: Final[str] = "Candidate prompt."
GRADER_MODEL_VARIABLE: Final[str] = "PROMPT_EVALS_GRADER_MODEL"
EVAL_SUITE_DEFINITION_FILE_NAME: Final[str] = "eval_suite.json"
DEFINITION_PROBLEM_COUNT_ENTRY_NAME: Final[str] = "DefinitionProblemCount"

type JsonObject = dict[str, object]


@dataclass(frozen=True)
class EntryMistakeDocument:
    """The part of a grade artifact's entry mistake these tests compare."""

    line_number: int
    mistake: str
    reference_category: str


@dataclass(frozen=True)
class AmountDiagnosisDocument:
    """The part of a grade artifact's amount diagnosis these tests compare."""

    category: str
    period: str | None
    reported_amount: str
    reference_amount: str
    explanations: tuple[tuple[EntryMistakeDocument, ...], ...]


@dataclass(frozen=True)
class CheckOutcomeDocument:
    check_name: str
    diagnoses: tuple[AmountDiagnosisDocument, ...]


@dataclass(frozen=True)
class TrialGradeDocument:
    check_outcomes: tuple[CheckOutcomeDocument, ...]


def create_trial_session(answer_text: str) -> ScriptedEventStreamSession:
    return ScriptedEventStreamSession(
        final_text=answer_text,
        scripted_tool_calls=(
            ScriptedClaudeToolCall(
                tool_name="Bash", tool_input={"command": "python totals.py"}, tool_result_text=RandomDataGenerator.create_random_word()
            ),
        ),
    )


def create_candidate_evaluation_request(sample_eval_suite: SampleEvalSuite, repetitions: int) -> EvaluationRequest:
    return EvaluationRequest(
        coding_assistant=CodingAssistant.CLAUDE_CODE,
        eval_suite_directory=sample_eval_suite.eval_suite_directory,
        model_name=f"model-{RandomDataGenerator.create_random_word()}",
        effort_level=EffortLevel.MEDIUM,
        repetitions=repetitions,
        variant_names=(CANDIDATE_VARIANT_NAME,),
    )


def create_domain_facade_for(test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli) -> DomainFacade:
    return create_domain_facade(test_mediator_coding_assistant_cli, {GRADER_MODEL_VARIABLE: f"grader-{RandomDataGenerator.create_random_word()}"})


def describe_entry(sample_ledger_entry: SampleLedgerEntry) -> str:
    return f'line {sample_ledger_entry.line_number} "{sample_ledger_entry.source_text}"'


def read_first_trial_grade_document(artifact_recorder: ArtifactRecorder) -> TrialGradeDocument:
    trial_grade_artifacts: list[EvaluationArtifact] = [
        evaluation_artifact
        for evaluation_artifact in artifact_recorder.evaluation_artifacts
        if evaluation_artifact.artifact_type == EvaluationArtifactType.TRIAL_GRADE
    ]
    trial_grade_json_object: JsonObject = cast(JsonObject, json.loads(trial_grade_artifacts[0].content.decode("utf-8")))
    return TrialGradeDocument(
        check_outcomes=tuple(
            CheckOutcomeDocument(
                check_name=cast(str, check_outcome_json_object["check_name"]),
                diagnoses=tuple(
                    AmountDiagnosisDocument(
                        category=cast(str, diagnosis_json_object["category"]),
                        period=cast(str | None, diagnosis_json_object["period"]),
                        reported_amount=cast(str, diagnosis_json_object["reported_amount"]),
                        reference_amount=cast(str, diagnosis_json_object["reference_amount"]),
                        explanations=tuple(
                            tuple(
                                EntryMistakeDocument(
                                    line_number=cast(int, entry_mistake_json_object["line_number"]),
                                    mistake=cast(str, entry_mistake_json_object["mistake"]),
                                    reference_category=cast(str, entry_mistake_json_object["reference_category"]),
                                )
                                for entry_mistake_json_object in explanation_json_objects
                            )
                            for explanation_json_objects in cast(list[list[JsonObject]], diagnosis_json_object["explanations"])
                        ),
                    )
                    for diagnosis_json_object in cast(list[JsonObject], check_outcome_json_object["diagnoses"])
                ),
            )
            for check_outcome_json_object in cast(list[JsonObject], trial_grade_json_object["check_outcomes"])
        )
    )


def retrieve_check_outcome_document(trial_grade_document: TrialGradeDocument, check_name: str) -> CheckOutcomeDocument:
    return next(
        check_outcome_document for check_outcome_document in trial_grade_document.check_outcomes if check_outcome_document.check_name == check_name
    )


def move_reference_ledger_into_inputs(eval_suite_directory: Path) -> str:
    """Copies the ledger into the case's inputs directory and points the case at that copy; returns the copy's suite-relative path."""
    eval_suite_definition: JsonObject = cast(
        JsonObject, json.loads((eval_suite_directory / EVAL_SUITE_DEFINITION_FILE_NAME).read_text(encoding="utf-8"))
    )
    case_object: JsonObject = cast(list[JsonObject], eval_suite_definition["cases"])[0]
    ledger_inside_inputs: str = f"{case_object['inputs_directory']}/reference_ledger.json"
    (eval_suite_directory / ledger_inside_inputs).write_text(
        (eval_suite_directory / CASE_REFERENCE_LEDGER_FILE).read_text(encoding="utf-8"), encoding="utf-8"
    )
    case_object["reference_ledger_file"] = ledger_inside_inputs
    SampleEvalSuiteBuilder.write_eval_suite_definition(eval_suite_directory, eval_suite_definition)
    return ledger_inside_inputs


@pytest.mark.acceptance
class TestRunEvaluationFailureDiagnosis:
    async def test_RunEvaluation_WhenEveryRunLeavesOutTheSameLedgerEntry_ThenTheFailureReasonsAndOneFailureCauseNameThatEntry(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        sample_reference_ledger: SampleReferenceLedger = SampleReferenceLedgerBuilder.write_sample_reference_ledger(sample_eval_suite)
        left_out_sample_ledger_entry: SampleLedgerEntry = sample_reference_ledger.member_entries[1]
        reported_total: Decimal = sample_reference_ledger.total_amount - left_out_sample_ledger_entry.amount
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions(
            (CANDIDATE_PROMPT_MARKER,), create_trial_session(f"Candidate answer {RandomDataGenerator.create_random_sentence()}")
        )
        test_mediator_coding_assistant_cli.script_sessions((FACT_EXTRACTION_PROMPT_HEADING,), create_extraction_session(f"${reported_total}", "over"))
        test_mediator_coding_assistant_cli.script_sessions(
            (JUDGMENT_PROMPT_HEADING,), create_judge_session(is_passed=True, reason=RandomDataGenerator.create_random_sentence())
        )
        evaluation_request: EvaluationRequest = create_candidate_evaluation_request(sample_eval_suite, repetitions=2)
        expected_rows: list[ExpectedScorecardRow] = create_expected_rows_for_every_check(CANDIDATE_VARIANT_NAME, trial_count=2, passed_count=2)
        expected_rows[0] = ExpectedScorecardRow(
            check_name=TOTAL_AMOUNT_CHECK_NAME,
            variant_name=CANDIDATE_VARIANT_NAME,
            trial_count=2,
            passed_count=0,
            errored_count=0,
            meets_minimum_pass_rate=False,
            failure_reason_phrases=("Likely cause:", f"left out {describe_entry(left_out_sample_ledger_entry)}"),
        )
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(passes_gate=False, expected_scorecard_rows=tuple(expected_rows))
        # The same mistake in every run is one failure cause that occurred once per run.
        expected_failure_causes: tuple[ExpectedFailureCause, ...] = (
            ExpectedFailureCause(
                occurrence_count=evaluation_request.repetitions, cause_summary_phrases=(describe_entry(left_out_sample_ledger_entry),)
            ),
        )

        # Act
        actual_scorecard: Scorecard = await create_domain_facade_for(test_mediator_coding_assistant_cli).run_evaluation(
            evaluation_request, ArtifactRecorder().record_evaluation_artifact
        )

        # Assert
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)
        FailureCauseAsserter.assert_expected_and_actual_are_equal(expected_failure_causes, actual_scorecard.failure_causes)

    async def test_RunEvaluation_WhenAnAmountCheckIsDiagnosed_ThenTheGradeArtifactRecordsTheMistakenEntry(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        sample_reference_ledger: SampleReferenceLedger = SampleReferenceLedgerBuilder.write_sample_reference_ledger(sample_eval_suite)
        included_sample_ledger_entry: SampleLedgerEntry = sample_reference_ledger.other_category_entry
        reported_total: Decimal = sample_reference_ledger.total_amount + included_sample_ledger_entry.amount
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions(
            (CANDIDATE_PROMPT_MARKER,), create_trial_session(f"Candidate answer {RandomDataGenerator.create_random_sentence()}")
        )
        test_mediator_coding_assistant_cli.script_sessions((FACT_EXTRACTION_PROMPT_HEADING,), create_extraction_session(str(reported_total), "over"))
        test_mediator_coding_assistant_cli.script_sessions(
            (JUDGMENT_PROMPT_HEADING,), create_judge_session(is_passed=True, reason=RandomDataGenerator.create_random_sentence())
        )
        artifact_recorder: ArtifactRecorder = ArtifactRecorder()
        expected_amount_diagnosis_documents: tuple[AmountDiagnosisDocument, ...] = (
            AmountDiagnosisDocument(
                category=sample_reference_ledger.category,
                period=sample_reference_ledger.period,
                reported_amount=str(reported_total),
                reference_amount=str(sample_reference_ledger.total_amount),
                explanations=(
                    (
                        EntryMistakeDocument(
                            line_number=included_sample_ledger_entry.line_number,
                            mistake="wrongly_included",
                            reference_category=included_sample_ledger_entry.category,
                        ),
                    ),
                ),
            ),
        )

        # Act
        await create_domain_facade_for(test_mediator_coding_assistant_cli).run_evaluation(
            create_candidate_evaluation_request(sample_eval_suite, repetitions=1), artifact_recorder.record_evaluation_artifact
        )

        # Assert
        check_outcome_document: CheckOutcomeDocument = retrieve_check_outcome_document(
            read_first_trial_grade_document(artifact_recorder), TOTAL_AMOUNT_CHECK_NAME
        )
        actual_amount_diagnosis_documents: tuple[AmountDiagnosisDocument, ...] = check_outcome_document.diagnoses
        assert actual_amount_diagnosis_documents == expected_amount_diagnosis_documents, (
            f"the {TOTAL_AMOUNT_CHECK_NAME} outcome in the first trial's grade artifact must record one diagnosis naming "
            f"{describe_entry(included_sample_ledger_entry)} as wrongly included; "
            f"expected {expected_amount_diagnosis_documents}; actual {actual_amount_diagnosis_documents}"
        )

    async def test_RunEvaluation_WhenTheJudgeDisputesAnAmountThatIsALedgerTotal_ThenTheJudgeCheckFailureNamesTheMistakenEntry(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        sample_reference_ledger: SampleReferenceLedger = SampleReferenceLedgerBuilder.write_sample_reference_ledger(sample_eval_suite)
        included_sample_ledger_entry: SampleLedgerEntry = sample_reference_ledger.other_category_entry
        disputed_answer_amount: Decimal = sample_reference_ledger.total_amount + included_sample_ledger_entry.amount
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions(
            (CANDIDATE_PROMPT_MARKER,), create_trial_session(f"Candidate answer {RandomDataGenerator.create_random_sentence()}")
        )
        test_mediator_coding_assistant_cli.script_sessions(
            (FACT_EXTRACTION_PROMPT_HEADING,), create_extraction_session(str(sample_reference_ledger.total_amount), "over")
        )
        test_mediator_coding_assistant_cli.script_sessions(
            (JUDGMENT_PROMPT_HEADING,),
            create_judge_session(
                is_passed=False,
                reason=RandomDataGenerator.create_random_sentence(),
                disputed_amounts=(
                    ScriptedDisputedAmount(
                        description=RandomDataGenerator.create_random_sentence(),
                        answer_amount_text=f"${disputed_answer_amount:,}",
                        reference_amount_text=f"${sample_reference_ledger.total_amount:,}",
                    ),
                ),
            ),
        )
        expected_rows: list[ExpectedScorecardRow] = create_expected_rows_for_every_check(CANDIDATE_VARIANT_NAME, trial_count=1, passed_count=1)
        expected_rows[3] = ExpectedScorecardRow(
            check_name=TABLES_FIRST_CHECK_NAME,
            variant_name=CANDIDATE_VARIANT_NAME,
            trial_count=1,
            passed_count=0,
            errored_count=0,
            meets_minimum_pass_rate=False,
            failure_reason_phrases=(
                f"counted {describe_entry(included_sample_ledger_entry)}",
                f"which the reference puts in {included_sample_ledger_entry.category}",
            ),
        )
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(passes_gate=False, expected_scorecard_rows=tuple(expected_rows))

        # Act
        actual_scorecard: Scorecard = await create_domain_facade_for(test_mediator_coding_assistant_cli).run_evaluation(
            create_candidate_evaluation_request(sample_eval_suite, repetitions=1), ArtifactRecorder().record_evaluation_artifact
        )

        # Assert
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)

    async def test_RunEvaluation_WhenAllChecksPass_ThenNoFailureCauseIsReported(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        sample_reference_ledger: SampleReferenceLedger = SampleReferenceLedgerBuilder.write_sample_reference_ledger(sample_eval_suite)
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions(
            (CANDIDATE_PROMPT_MARKER,), create_trial_session(f"Candidate answer {RandomDataGenerator.create_random_sentence()}")
        )
        test_mediator_coding_assistant_cli.script_sessions(
            (FACT_EXTRACTION_PROMPT_HEADING,), create_extraction_session(str(sample_reference_ledger.total_amount), "over")
        )
        test_mediator_coding_assistant_cli.script_sessions(
            (JUDGMENT_PROMPT_HEADING,), create_judge_session(is_passed=True, reason=RandomDataGenerator.create_random_sentence())
        )
        expected_gate_outcome: tuple[bool, tuple[FailureCause, ...]] = (True, ())

        # Act
        actual_scorecard: Scorecard = await create_domain_facade_for(test_mediator_coding_assistant_cli).run_evaluation(
            create_candidate_evaluation_request(sample_eval_suite, repetitions=1), ArtifactRecorder().record_evaluation_artifact
        )

        # Assert
        actual_gate_outcome: tuple[bool, tuple[FailureCause, ...]] = (actual_scorecard.passes_gate, actual_scorecard.failure_causes)
        assert actual_gate_outcome == expected_gate_outcome, (
            "when every check passes, the gate must pass with no failure causes; "
            f"(passes gate, failure causes) expected {expected_gate_outcome}; actual {actual_gate_outcome}"
        )

    async def test_RunEvaluation_WhenTheJudgeReturnsNoDisputedAmountsTwice_ThenTheJudgeCheckIsErroredNotFailed(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = TestMediatorCodingAssistantCli()
        test_mediator_coding_assistant_cli.script_sessions(
            (CANDIDATE_PROMPT_MARKER,), create_trial_session(f"Candidate answer {RandomDataGenerator.create_random_sentence()}")
        )
        test_mediator_coding_assistant_cli.script_sessions(
            (FACT_EXTRACTION_PROMPT_HEADING,), create_extraction_session(sample_eval_suite.expected_total_amount, "over")
        )
        test_mediator_coding_assistant_cli.script_sessions(
            (JUDGMENT_PROMPT_HEADING,),
            ScriptedEventStreamSession(structured_output={"passed": False, "reason": RandomDataGenerator.create_random_sentence()}),
        )
        expected_rows: list[ExpectedScorecardRow] = create_expected_rows_for_every_check(CANDIDATE_VARIANT_NAME, trial_count=1, passed_count=1)
        expected_rows[3] = ExpectedScorecardRow(
            check_name=TABLES_FIRST_CHECK_NAME,
            variant_name=CANDIDATE_VARIANT_NAME,
            trial_count=1,
            passed_count=0,
            errored_count=1,
            meets_minimum_pass_rate=False,
            failure_reason_phrases=("disputed_amounts",),
        )
        expected_scorecard: ExpectedScorecard = ExpectedScorecard(passes_gate=False, expected_scorecard_rows=tuple(expected_rows))

        # Act
        actual_scorecard: Scorecard = await create_domain_facade_for(test_mediator_coding_assistant_cli).run_evaluation(
            create_candidate_evaluation_request(sample_eval_suite, repetitions=1), ArtifactRecorder().record_evaluation_artifact
        )

        # Assert
        ScorecardAsserter.assert_expected_and_actual_are_equal(expected_scorecard, actual_scorecard.passes_gate, actual_scorecard.scorecard_rows)


@pytest.mark.acceptance
class TestRunEvaluationReferenceLedgerInvalidInput:
    async def test_RunEvaluation_WhenTheLedgerTotalDisagreesWithTheExpectedFact_ThenEvalSuiteDefinitionInvalidExceptionNamesTheFact(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        sample_reference_ledger: SampleReferenceLedger = SampleReferenceLedgerBuilder.write_sample_reference_ledger(sample_eval_suite)
        disagreeing_amount: Decimal = sample_reference_ledger.total_amount + Decimal(RandomDataGenerator.create_random_amount_text())
        SampleEvalSuiteBuilder.write_expected_facts(
            sample_eval_suite.eval_suite_directory, {TOTAL_FACT_NAME: [str(disagreeing_amount)], "status": ["over"]}
        )
        expected_message_phrases: tuple[str, ...] = (
            f"fact '{TOTAL_FACT_NAME}' accepts {disagreeing_amount}",
            f"the reference ledger totals it as {sample_reference_ledger.total_amount}",
        )
        # Both phrases describe the one disagreement between the expected fact and the ledger total.
        expected_contextual_entries_by_name: dict[str, object] = {DEFINITION_PROBLEM_COUNT_ENTRY_NAME: 1}

        # Act
        with pytest.raises(EvalSuiteDefinitionInvalidException) as exception_info:
            await create_domain_facade_for(TestMediatorCodingAssistantCli()).run_evaluation(
                create_candidate_evaluation_request(sample_eval_suite, repetitions=1), ArtifactRecorder().record_evaluation_artifact
            )

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=EvalSuiteDefinitionInvalidException,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_exception=exception_info.value,
        )

    async def test_RunEvaluation_WhenLedgerEntriesAreMalformed_ThenEveryEntryProblemIsReportedTogether(self, tmp_path: Path) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        unparseable_amount: str = f"about {RandomDataGenerator.create_random_word()}"
        own_category: str = f"category-{RandomDataGenerator.create_random_word()}"
        SampleReferenceLedgerBuilder.write_reference_ledger_document(
            sample_eval_suite.eval_suite_directory,
            {
                "entries": [
                    {
                        "line_number": 0,
                        "source_text": RandomDataGenerator.create_random_sentence(),
                        "period": RandomDataGenerator.create_random_word(),
                        "amount": unparseable_amount,
                        "category": own_category,
                        "alternative_categories": [own_category],
                        "policy_name": None,
                        "is_counted": "yes",
                        "note": None,
                    }
                ],
                "amount_facts": {},
            },
        )
        expected_message_phrases: tuple[str, ...] = (
            f"{CASE_REFERENCE_LEDGER_FILE} entry 1 needs a positive integer 'line_number'",
            f"has 'amount' '{unparseable_amount}', which is not a plain number",
            f"lists its own category '{own_category}' as an alternative",
            "needs a 'policy_name' exactly when it lists alternative_categories",
            "needs a boolean 'is_counted'",
        )
        expected_contextual_entries_by_name: dict[str, object] = {DEFINITION_PROBLEM_COUNT_ENTRY_NAME: len(expected_message_phrases)}

        # Act
        with pytest.raises(EvalSuiteDefinitionInvalidException) as exception_info:
            await create_domain_facade_for(TestMediatorCodingAssistantCli()).run_evaluation(
                create_candidate_evaluation_request(sample_eval_suite, repetitions=1), ArtifactRecorder().record_evaluation_artifact
            )

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=EvalSuiteDefinitionInvalidException,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_exception=exception_info.value,
        )

    async def test_RunEvaluation_WhenTheLedgerSitsInsideTheInputsDirectory_ThenEvalSuiteDefinitionInvalidExceptionSaysTheTrialCouldReadIt(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        sample_eval_suite: SampleEvalSuite = SampleEvalSuiteBuilder.write_sample_eval_suite(tmp_path)
        SampleReferenceLedgerBuilder.write_sample_reference_ledger(sample_eval_suite)
        ledger_inside_inputs: str = move_reference_ledger_into_inputs(sample_eval_suite.eval_suite_directory)
        expected_message_phrases: tuple[str, ...] = (f"the file '{ledger_inside_inputs}' is inside the inputs directory", "the trial could read it")
        # Both phrases describe the one ledger file placed inside the one case's inputs directory.
        expected_contextual_entries_by_name: dict[str, object] = {DEFINITION_PROBLEM_COUNT_ENTRY_NAME: 1}

        # Act
        with pytest.raises(EvalSuiteDefinitionInvalidException) as exception_info:
            await create_domain_facade_for(TestMediatorCodingAssistantCli()).run_evaluation(
                create_candidate_evaluation_request(sample_eval_suite, repetitions=1), ArtifactRecorder().record_evaluation_artifact
            )

        # Assert
        ExceptionAsserter.assert_expected_and_actual_are_equal(
            expected_exception_type=EvalSuiteDefinitionInvalidException,
            expected_message_phrases=expected_message_phrases,
            expected_contextual_entries_by_name=expected_contextual_entries_by_name,
            actual_exception=exception_info.value,
        )
