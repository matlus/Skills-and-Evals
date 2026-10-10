from decimal import Decimal
from typing import Final, final

from prompt_evals.managers.engines.processors.fact_check_processors.amount_text_processor import AmountTextProcessor
from prompt_evals.managers.models.eval_suite_models import AmountCheckDefinition
from prompt_evals.managers.models.grading_models import CheckOutcome, CheckStatus
from prompt_evals.managers.models.trial_models import TrialIdentity

# Answers round to the cent, so anything within one cent of an accepted amount is the same amount.
AMOUNT_TOLERANCE: Final[Decimal] = Decimal("0.01")


@final
class AmountCheckGradingProcessor:
    @staticmethod
    def grade_amount_check(
        amount_check_definition: AmountCheckDefinition,
        reported_value: str | None,
        accepted_values: tuple[str, ...],
        trial_identity: TrialIdentity,
    ) -> CheckOutcome:
        accepted_values_display: str = " or ".join(accepted_values)
        reported_amount: Decimal | None = None if reported_value is None else AmountTextProcessor.parse_reported_amount(reported_value)
        return CheckOutcome(
            check_name=amount_check_definition.check_name,
            trial_identity=trial_identity,
            check_status=AmountCheckGradingProcessor._decide_check_status(reported_amount, accepted_values),
            reason=AmountCheckGradingProcessor._describe_outcome(
                amount_check_definition.fact_name, reported_value, reported_amount, accepted_values_display
            ),
            amount_discrepancy_diagnoses=(),
        )

    @staticmethod
    def _decide_check_status(reported_amount: Decimal | None, accepted_values: tuple[str, ...]) -> CheckStatus:
        if reported_amount is None:
            return CheckStatus.FAILED
        is_accepted: bool = any(abs(reported_amount - Decimal(accepted_value)) <= AMOUNT_TOLERANCE for accepted_value in accepted_values)
        return CheckStatus.PASSED if is_accepted else CheckStatus.FAILED

    @staticmethod
    def _describe_outcome(fact_name: str, reported_value: str | None, reported_amount: Decimal | None, accepted_values_display: str) -> str:
        if reported_value is None:
            return f"the answer does not report {fact_name}; expected {accepted_values_display}"
        if reported_amount is None:
            return f"the reported value '{reported_value}' is not an amount; expected {accepted_values_display}"
        return f"reported {reported_amount}; expected {accepted_values_display}"
