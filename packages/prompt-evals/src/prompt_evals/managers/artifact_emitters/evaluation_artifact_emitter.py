import dataclasses
import json
from typing import Final, final

from prompt_evals.managers.artifact_emitters.artifact_document_models import (
    AmountDiagnosisDocument,
    CheckOutcomeDocument,
    EntryMistakeDocument,
    TrialGradeDocument,
    TrialTimingDocument,
)
from prompt_evals.managers.exceptions.artifact_exceptions import ArtifactCallbackException
from prompt_evals.managers.models.artifact_models import EvaluationArtifact, EvaluationArtifactCallback, EvaluationArtifactType
from prompt_evals.managers.models.diagnosis_models import AmountDiscrepancyDiagnosis, EntryMistake
from prompt_evals.managers.models.grading_models import CheckOutcome, TrialGrade
from prompt_evals.managers.models.scorecard_models import Scorecard
from prompt_evals.managers.models.trial_models import CompletedTrial, ErroredTrial, TrialIdentity, TrialRecord

TEXT_ENCODING: Final[str] = "utf-8"
EVALUATION_RUN_ORIGIN: Final[str] = "the evaluation run"


@final
class EvaluationArtifactEmitter:
    """The single owner of artifact naming. Hosts receive self-describing artifacts and decide where to persist them."""

    @staticmethod
    def emit_trial_records(evaluation_artifact_callback: EvaluationArtifactCallback, trial_records: tuple[TrialRecord, ...]) -> None:
        for trial_record in trial_records:
            EvaluationArtifactEmitter._emit_trial_record(evaluation_artifact_callback, trial_record)

    @staticmethod
    def emit_trial_grades(evaluation_artifact_callback: EvaluationArtifactCallback, trial_grades: tuple[TrialGrade, ...]) -> None:
        for trial_grade in trial_grades:
            EvaluationArtifactEmitter._emit(
                evaluation_artifact_callback,
                EvaluationArtifactType.TRIAL_GRADE,
                trial_grade.trial_identity,
                EvaluationArtifactEmitter._serialize_trial_grade(trial_grade),
            )

    @staticmethod
    def emit_scorecard(evaluation_artifact_callback: EvaluationArtifactCallback, scorecard: Scorecard, scorecard_report: str) -> None:
        EvaluationArtifactEmitter._emit(
            evaluation_artifact_callback,
            EvaluationArtifactType.SCORECARD,
            None,
            EvaluationArtifactEmitter._serialize_scorecard(scorecard),
        )
        EvaluationArtifactEmitter._emit(evaluation_artifact_callback, EvaluationArtifactType.SCORECARD_REPORT, None, scorecard_report)

    @staticmethod
    def _serialize_scorecard(scorecard: Scorecard) -> str:
        return json.dumps(dataclasses.asdict(scorecard), indent=2, ensure_ascii=False)

    @staticmethod
    def _emit_trial_record(evaluation_artifact_callback: EvaluationArtifactCallback, trial_record: TrialRecord) -> None:
        match trial_record:
            case CompletedTrial(trial_identity=trial_identity, llm_session_transcript=llm_session_transcript):
                EvaluationArtifactEmitter._emit(
                    evaluation_artifact_callback,
                    EvaluationArtifactType.TRIAL_EVENT_STREAM,
                    trial_identity,
                    llm_session_transcript.event_stream_text,
                )
                EvaluationArtifactEmitter._emit(
                    evaluation_artifact_callback, EvaluationArtifactType.TRIAL_ANSWER, trial_identity, llm_session_transcript.final_text
                )
            case ErroredTrial(trial_identity=trial_identity, error_description=error_description):
                EvaluationArtifactEmitter._emit(evaluation_artifact_callback, EvaluationArtifactType.TRIAL_ERROR, trial_identity, error_description)
        EvaluationArtifactEmitter._emit(
            evaluation_artifact_callback,
            EvaluationArtifactType.TRIAL_TIMING,
            trial_record.trial_identity,
            EvaluationArtifactEmitter._serialize_trial_timing(trial_record),
        )

    @staticmethod
    def _serialize_trial_timing(trial_record: TrialRecord) -> str:
        return json.dumps(dataclasses.asdict(TrialTimingDocument(answer_duration_seconds=trial_record.answer_duration_seconds)), indent=2)

    @staticmethod
    def _serialize_trial_grade(trial_grade: TrialGrade) -> str:
        trial_grade_document: TrialGradeDocument = EvaluationArtifactEmitter._map_to_trial_grade_document(trial_grade)
        return json.dumps(dataclasses.asdict(trial_grade_document), indent=2, ensure_ascii=False)

    @staticmethod
    def _map_to_trial_grade_document(trial_grade: TrialGrade) -> TrialGradeDocument:
        return TrialGradeDocument(
            trial_identity=trial_grade.trial_identity,
            extracted_facts=None
            if trial_grade.extracted_facts is None
            else {extracted_fact.fact_name: extracted_fact.reported_value for extracted_fact in trial_grade.extracted_facts.extracted_facts},
            check_outcomes=tuple(
                EvaluationArtifactEmitter._map_to_check_outcome_document(check_outcome) for check_outcome in trial_grade.check_outcomes
            ),
            grading_duration_seconds=trial_grade.grading_duration_seconds,
        )

    @staticmethod
    def _map_to_check_outcome_document(check_outcome: CheckOutcome) -> CheckOutcomeDocument:
        return CheckOutcomeDocument(
            check_name=check_outcome.check_name,
            check_status=check_outcome.check_status.value,
            reason=check_outcome.reason,
            diagnoses=tuple(
                EvaluationArtifactEmitter._map_to_amount_diagnosis_document(amount_discrepancy_diagnosis)
                for amount_discrepancy_diagnosis in check_outcome.amount_discrepancy_diagnoses
            ),
        )

    @staticmethod
    def _map_to_amount_diagnosis_document(amount_discrepancy_diagnosis: AmountDiscrepancyDiagnosis) -> AmountDiagnosisDocument:
        return AmountDiagnosisDocument(
            category=amount_discrepancy_diagnosis.ledger_bucket.category,
            period=amount_discrepancy_diagnosis.ledger_bucket.period,
            reported_amount=str(amount_discrepancy_diagnosis.reported_amount),
            reference_amount=str(amount_discrepancy_diagnosis.reference_amount),
            accepted_policies=amount_discrepancy_diagnosis.accepted_policy_names,
            cause=amount_discrepancy_diagnosis.cause_description,
            explanations=tuple(
                tuple(
                    EvaluationArtifactEmitter._map_to_entry_mistake_document(entry_mistake)
                    for entry_mistake in discrepancy_explanation.entry_mistakes
                )
                for discrepancy_explanation in amount_discrepancy_diagnosis.discrepancy_explanations
            ),
        )

    @staticmethod
    def _map_to_entry_mistake_document(entry_mistake: EntryMistake) -> EntryMistakeDocument:
        return EntryMistakeDocument(
            line_number=entry_mistake.ledger_entry.line_number,
            source_text=entry_mistake.ledger_entry.source_text,
            mistake=entry_mistake.entry_mistake_kind.value,
            amount_effect=str(entry_mistake.amount_effect),
            reference_category=entry_mistake.ledger_entry.category,
            reference_period=entry_mistake.ledger_entry.period,
        )

    @staticmethod
    def _emit(
        evaluation_artifact_callback: EvaluationArtifactCallback,
        evaluation_artifact_type: EvaluationArtifactType,
        trial_identity: TrialIdentity | None,
        content_text: str,
    ) -> None:
        evaluation_artifact: EvaluationArtifact = EvaluationArtifact(
            artifact_type=evaluation_artifact_type,
            trial_identity=trial_identity,
            content=content_text.encode(TEXT_ENCODING),
            filename_suffix=f"{evaluation_artifact_type.file_stem}.{evaluation_artifact_type.file_extension}",
            content_type=evaluation_artifact_type.content_type,
        )
        try:
            evaluation_artifact_callback(evaluation_artifact)
        except Exception as callback_failure:
            raise ArtifactCallbackException(
                evaluation_artifact_type.value, evaluation_artifact.filename_suffix, EvaluationArtifactEmitter._describe_origin(trial_identity)
            ) from callback_failure

    @staticmethod
    def _describe_origin(trial_identity: TrialIdentity | None) -> str:
        if trial_identity is None:
            return EVALUATION_RUN_ORIGIN
        return f"trial {trial_identity.variant_name} / {trial_identity.case_name} / run {trial_identity.repetition_number}"
