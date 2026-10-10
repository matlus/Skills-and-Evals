from typing import final

from prompt_evals.managers.models.eval_suite_models import FactValueCheckDefinition
from prompt_evals.managers.models.grading_models import CheckOutcome, CheckStatus
from prompt_evals.managers.models.trial_models import TrialIdentity


@final
class FactValueCheckGradingProcessor:
    """Compares a reported fact with the accepted values, ignoring case and surrounding whitespace."""

    @staticmethod
    def grade_fact_value_check(
        fact_value_check_definition: FactValueCheckDefinition,
        reported_value: str | None,
        accepted_values: tuple[str, ...],
        trial_identity: TrialIdentity,
    ) -> CheckOutcome:
        normalized_accepted_values: set[str] = {accepted_value.strip().casefold() for accepted_value in accepted_values}
        is_accepted: bool = reported_value is not None and reported_value.strip().casefold() in normalized_accepted_values
        return CheckOutcome(
            check_name=fact_value_check_definition.check_name,
            trial_identity=trial_identity,
            check_status=CheckStatus.PASSED if is_accepted else CheckStatus.FAILED,
            reason=f"reported {reported_value if reported_value is not None else 'nothing'}; expected {' or '.join(accepted_values)}",
            amount_discrepancy_diagnoses=(),
        )
