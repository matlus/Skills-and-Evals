from collections.abc import Iterable
from typing import final

from prompt_evals.managers.models.eval_suite_models import CheckDefinition, EvalSuite
from prompt_evals.managers.models.evaluation_models import TrialRunDescription
from prompt_evals.managers.models.grading_models import CheckOutcome, CheckStatus, TrialGrade
from prompt_evals.managers.models.scorecard_models import FailureCause, Scorecard, ScorecardRow


@final
class ScorecardAggregationProcessor:
    """Turns per-trial outcomes into pass rates: one row per check per graded prompt variant."""

    @staticmethod
    def aggregate_scorecard(eval_suite: EvalSuite, trial_run_description: TrialRunDescription, trial_grades: tuple[TrialGrade, ...]) -> Scorecard:
        scorecard_rows: tuple[ScorecardRow, ...] = ScorecardAggregationProcessor._build_scorecard_rows(eval_suite, trial_grades)
        return Scorecard(
            eval_suite_name=eval_suite.eval_suite_name,
            coding_assistant=trial_run_description.coding_assistant,
            model_name=trial_run_description.model_name,
            effort_level=trial_run_description.effort_level,
            repetitions=trial_run_description.repetitions,
            scorecard_rows=scorecard_rows,
            failure_causes=ScorecardAggregationProcessor._group_failure_causes(trial_grades),
            passes_gate=ScorecardAggregationProcessor._decide_gate(scorecard_rows),
        )

    @staticmethod
    def _group_failure_causes(trial_grades: Iterable[TrialGrade]) -> tuple[FailureCause, ...]:
        # The summary leaves out the amounts, so one mistake repeated across runs is listed once with every run that made it.
        occurrence_labels_by_cause_summary: dict[str, list[str]] = {}
        for trial_grade in trial_grades:
            for check_outcome in trial_grade.check_outcomes:
                for amount_discrepancy_diagnosis in check_outcome.amount_discrepancy_diagnoses:
                    occurrence_label: str = (
                        f"{check_outcome.trial_identity.variant_name} / {ScorecardAggregationProcessor._label_trial(check_outcome)} / "
                        f"{check_outcome.check_name}"
                    )
                    occurrence_labels_by_cause_summary.setdefault(amount_discrepancy_diagnosis.cause_summary, []).append(occurrence_label)
        failure_causes: list[FailureCause] = [
            FailureCause(cause_summary=cause_summary, occurrence_labels=tuple(occurrence_labels))
            for cause_summary, occurrence_labels in occurrence_labels_by_cause_summary.items()
        ]
        failure_causes.sort(key=lambda failure_cause: -len(failure_cause.occurrence_labels))
        return tuple(failure_causes)

    @staticmethod
    def _build_scorecard_rows(eval_suite: EvalSuite, trial_grades: tuple[TrialGrade, ...]) -> tuple[ScorecardRow, ...]:
        graded_variant_names: set[str] = {trial_grade.trial_identity.variant_name for trial_grade in trial_grades}
        return tuple(
            ScorecardAggregationProcessor._build_scorecard_row(check_definition, prompt_variant.variant_name, eval_suite, trial_grades)
            for check_definition in eval_suite.check_definitions
            for prompt_variant in eval_suite.prompt_variants
            if prompt_variant.variant_name in graded_variant_names
        )

    @staticmethod
    def _decide_gate(scorecard_rows: tuple[ScorecardRow, ...]) -> bool:
        gated_rows: list[ScorecardRow] = [scorecard_row for scorecard_row in scorecard_rows if scorecard_row.is_gated]
        # A run that never evaluated a gated variant has proven nothing about the prompt under test.
        return bool(gated_rows) and all(gated_row.meets_minimum_pass_rate for gated_row in gated_rows)

    @staticmethod
    def _build_scorecard_row(
        check_definition: CheckDefinition, variant_name: str, eval_suite: EvalSuite, trial_grades: tuple[TrialGrade, ...]
    ) -> ScorecardRow:
        check_outcomes: list[CheckOutcome] = ScorecardAggregationProcessor._select_check_outcomes(check_definition, variant_name, trial_grades)
        passed_count: int = sum(1 for check_outcome in check_outcomes if check_outcome.check_status == CheckStatus.PASSED)
        pass_rate: float = passed_count / len(check_outcomes) if check_outcomes else 0.0
        return ScorecardRow(
            check_name=check_definition.check_name,
            description=check_definition.description,
            variant_name=variant_name,
            trial_count=len(check_outcomes),
            passed_count=passed_count,
            errored_count=sum(1 for check_outcome in check_outcomes if check_outcome.check_status == CheckStatus.ERRORED),
            pass_rate=pass_rate,
            minimum_pass_rate=check_definition.minimum_pass_rate,
            is_gated=variant_name in eval_suite.gated_variant_names,
            meets_minimum_pass_rate=pass_rate >= check_definition.minimum_pass_rate,
            failure_reasons=tuple(
                ScorecardAggregationProcessor._describe_failure(check_outcome)
                for check_outcome in check_outcomes
                if check_outcome.check_status != CheckStatus.PASSED
            ),
        )

    @staticmethod
    def _select_check_outcomes(check_definition: CheckDefinition, variant_name: str, trial_grades: tuple[TrialGrade, ...]) -> list[CheckOutcome]:
        return [
            check_outcome
            for trial_grade in trial_grades
            if trial_grade.trial_identity.variant_name == variant_name
            for check_outcome in trial_grade.check_outcomes
            if check_outcome.check_name == check_definition.check_name
        ]

    @staticmethod
    def _describe_failure(check_outcome: CheckOutcome) -> str:
        cause_texts: str = "".join(
            f" Likely cause: {amount_discrepancy_diagnosis.cause_description}"
            for amount_discrepancy_diagnosis in check_outcome.amount_discrepancy_diagnoses
        )
        return f"{ScorecardAggregationProcessor._label_trial(check_outcome)}: [{check_outcome.check_status}] {check_outcome.reason}{cause_texts}"

    @staticmethod
    def _label_trial(check_outcome: CheckOutcome) -> str:
        return f"{check_outcome.trial_identity.case_name}/run-{check_outcome.trial_identity.repetition_number:02d}"
