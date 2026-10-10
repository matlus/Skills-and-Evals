from typing import assert_never, final

from prompt_evals.managers.engines.processors.fact_check_processors.amount_check_grading_processor import AmountCheckGradingProcessor
from prompt_evals.managers.engines.processors.fact_check_processors.fact_value_check_grading_processor import FactValueCheckGradingProcessor
from prompt_evals.managers.models.eval_suite_models import AmountCheckDefinition, ExpectedFact, FactValueCheckDefinition
from prompt_evals.managers.models.grading_models import (
    CheckOutcome,
    CheckStatus,
    FactExtractionAttempt,
    FailedFactExtraction,
    SucceededFactExtraction,
)
from prompt_evals.managers.models.trial_models import TrialIdentity


@final
class FactCheckGradingProcessor:
    """Grades a check on one fact the answer reports. When fact extraction failed, the check is errored: the answer was never read."""

    @staticmethod
    def grade_fact_check(
        fact_check_definition: AmountCheckDefinition | FactValueCheckDefinition,
        fact_extraction_attempt: FactExtractionAttempt,
        expected_facts: tuple[ExpectedFact, ...],
        trial_identity: TrialIdentity,
    ) -> CheckOutcome:
        match fact_extraction_attempt:
            case SucceededFactExtraction(extracted_facts=extracted_facts):
                return FactCheckGradingProcessor._grade_reported_value(
                    fact_check_definition,
                    extracted_facts.read_reported_value(fact_check_definition.fact_name),
                    FactCheckGradingProcessor._retrieve_accepted_values(expected_facts, fact_check_definition.fact_name),
                    trial_identity,
                )
            case FailedFactExtraction(failure_description=failure_description):
                # Only the fact-based checks depend on extraction; they are recorded as errored, the rest still run.
                return CheckOutcome(
                    check_name=fact_check_definition.check_name,
                    trial_identity=trial_identity,
                    check_status=CheckStatus.ERRORED,
                    reason=f"fact extraction failed: {failure_description}",
                    amount_discrepancy_diagnoses=(),
                )

    @staticmethod
    def _grade_reported_value(
        fact_check_definition: AmountCheckDefinition | FactValueCheckDefinition,
        reported_value: str | None,
        accepted_values: tuple[str, ...],
        trial_identity: TrialIdentity,
    ) -> CheckOutcome:
        match fact_check_definition:
            case AmountCheckDefinition():
                return AmountCheckGradingProcessor.grade_amount_check(fact_check_definition, reported_value, accepted_values, trial_identity)
            case FactValueCheckDefinition():
                return FactValueCheckGradingProcessor.grade_fact_value_check(fact_check_definition, reported_value, accepted_values, trial_identity)
            case _:
                assert_never(fact_check_definition)

    @staticmethod
    def _retrieve_accepted_values(expected_facts: tuple[ExpectedFact, ...], fact_name: str) -> tuple[str, ...]:
        # Suite validation guarantees every case has exactly one expected fact for each fact a check uses.
        accepted_values_per_match: list[tuple[str, ...]] = [
            expected_fact.accepted_values for expected_fact in expected_facts if expected_fact.fact_name == fact_name
        ]
        return accepted_values_per_match[0]
