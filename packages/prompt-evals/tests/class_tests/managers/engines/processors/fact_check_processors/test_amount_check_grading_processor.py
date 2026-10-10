from typing import Final

import pytest
from acceptance_support.random_data_generator import RandomDataGenerator

from prompt_evals.managers.engines.processors.fact_check_processors.amount_check_grading_processor import AmountCheckGradingProcessor
from prompt_evals.managers.models.eval_suite_models import AmountCheckDefinition
from prompt_evals.managers.models.grading_models import CheckOutcome, CheckStatus
from prompt_evals.managers.models.trial_models import TrialIdentity

ACCEPTED_AMOUNT: Final[str] = "398.69"


def create_amount_check_definition() -> AmountCheckDefinition:
    return AmountCheckDefinition(
        check_name=RandomDataGenerator.create_random_word(),
        description=RandomDataGenerator.create_random_sentence(),
        minimum_pass_rate=0.8,
        fact_name=RandomDataGenerator.create_random_word(),
    )


def create_trial_identity() -> TrialIdentity:
    return TrialIdentity(
        variant_name=RandomDataGenerator.create_random_word(), case_name=RandomDataGenerator.create_random_word(), repetition_number=1
    )


@pytest.mark.class_test
class TestAmountCheckGradingProcessor:
    @pytest.mark.parametrize(
        ("reported_value", "expected_reason_phrase"),
        [
            ("398.69", "reported 398.69;"),
            ("$398.69", "reported 398.69;"),
            ("398.70", "reported 398.70;"),
            ("398.68", "reported 398.68;"),
            (" 398.69 ", "reported 398.69;"),
        ],
    )
    def test_GradeAmountCheck_WhenReportedAmountIsWithinOneCent_ThenCheckPasses(self, reported_value: str, expected_reason_phrase: str) -> None:
        # Arrange
        expected_check_status: CheckStatus = CheckStatus.PASSED

        # Act
        actual_check_outcome: CheckOutcome = AmountCheckGradingProcessor.grade_amount_check(
            create_amount_check_definition(), reported_value, (ACCEPTED_AMOUNT,), create_trial_identity()
        )

        # Assert
        assert (actual_check_outcome.check_status, expected_reason_phrase in actual_check_outcome.reason) == (expected_check_status, True), (
            f"expected {expected_check_status} with a reason mentioning {expected_reason_phrase!r}; "
            f"actual {actual_check_outcome.check_status}: {actual_check_outcome.reason!r}"
        )

    @pytest.mark.parametrize(
        ("reported_value", "expected_reason_phrase"),
        [
            ("398.71", "reported 398.71;"),
            ("398.67", "reported 398.67;"),
            ("412.10", "reported 412.10;"),
            ("-398.69", "reported -398.69;"),
        ],
    )
    def test_GradeAmountCheck_WhenReportedAmountIsMoreThanOneCentAway_ThenCheckFails(self, reported_value: str, expected_reason_phrase: str) -> None:
        # Arrange
        expected_check_status: CheckStatus = CheckStatus.FAILED

        # Act
        actual_check_outcome: CheckOutcome = AmountCheckGradingProcessor.grade_amount_check(
            create_amount_check_definition(), reported_value, (ACCEPTED_AMOUNT,), create_trial_identity()
        )

        # Assert
        assert (actual_check_outcome.check_status, expected_reason_phrase in actual_check_outcome.reason) == (expected_check_status, True), (
            f"expected {expected_check_status} with a reason mentioning {expected_reason_phrase!r}; "
            f"actual {actual_check_outcome.check_status}: {actual_check_outcome.reason!r}"
        )

    def test_GradeAmountCheck_WhenThousandsSeparatorMatchesASecondAcceptedValue_ThenCheckPasses(self) -> None:
        # Arrange
        reported_value: str = "$1,631.82"
        accepted_values: tuple[str, ...] = ("1655.92", "1631.82")
        expected_check_status: CheckStatus = CheckStatus.PASSED
        expected_reason_phrase: str = "reported 1631.82; expected 1655.92 or 1631.82"

        # Act
        actual_check_outcome: CheckOutcome = AmountCheckGradingProcessor.grade_amount_check(
            create_amount_check_definition(), reported_value, accepted_values, create_trial_identity()
        )

        # Assert
        assert (actual_check_outcome.check_status, expected_reason_phrase in actual_check_outcome.reason) == (expected_check_status, True), (
            f"expected {expected_check_status} with a reason mentioning {expected_reason_phrase!r}; "
            f"actual {actual_check_outcome.check_status}: {actual_check_outcome.reason!r}"
        )

    @pytest.mark.parametrize(
        ("reported_value", "expected_reason_phrase"),
        [
            (None, "does not report"),
            ("about four hundred", "is not an amount"),
            ("NaN", "is not an amount"),
            ("sNaN", "is not an amount"),
            ("Infinity", "is not an amount"),
            ("1e1000000", "is not an amount"),
        ],
    )
    def test_GradeAmountCheck_WhenAmountIsMissingOrNotAPlausibleNumber_ThenCheckFailsAndSaysWhy(
        self, reported_value: str | None, expected_reason_phrase: str
    ) -> None:
        # Arrange
        expected_check_status: CheckStatus = CheckStatus.FAILED

        # Act
        actual_check_outcome: CheckOutcome = AmountCheckGradingProcessor.grade_amount_check(
            create_amount_check_definition(), reported_value, (ACCEPTED_AMOUNT,), create_trial_identity()
        )

        # Assert
        assert (actual_check_outcome.check_status, expected_reason_phrase in actual_check_outcome.reason) == (expected_check_status, True), (
            f"expected {expected_check_status} with a reason mentioning {expected_reason_phrase!r}; "
            f"actual {actual_check_outcome.check_status}: {actual_check_outcome.reason!r}"
        )
