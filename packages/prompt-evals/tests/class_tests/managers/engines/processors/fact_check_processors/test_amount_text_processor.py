from decimal import Decimal
from typing import Final

import pytest

from prompt_evals.managers.engines.processors.fact_check_processors.amount_text_processor import AmountTextProcessor

UNICODE_MINUS_SIGN: Final[str] = "\N{MINUS SIGN}"


@pytest.mark.class_test
class TestAmountTextProcessor:
    @pytest.mark.parametrize(
        ("reported_value", "expected_amount"),
        [
            ("$1,631.82", Decimal("1631.82")),
            ("-$68.00", Decimal("-68.00")),
            (f"{UNICODE_MINUS_SIGN}$68.00", Decimal("-68.00")),
        ],
        ids=["dollar-and-separator", "hyphen-minus", "unicode-minus"],
    )
    def test_ParseReportedAmount_WhenTheValueIsAFormattedAmount_ThenTheAmountIsRead(self, reported_value: str, expected_amount: Decimal) -> None:
        # Act
        actual_amount: Decimal | None = AmountTextProcessor.parse_reported_amount(reported_value)

        # Assert
        assert actual_amount == expected_amount, f"expected {expected_amount} for {reported_value!r}; actual {actual_amount}"

    @pytest.mark.parametrize(
        ("quoted_text", "expected_amount_and_exponent"),
        [
            ("about $2,996", (Decimal(2996), 0)),
            ("approx. $2,996", (Decimal(2996), 0)),
            ("$2,996.00", (Decimal("2996.00"), -2)),
        ],
        ids=["whole-dollar", "whole-dollar-after-an-abbreviation", "cents"],
    )
    def test_ParseQuotedAmount_WhenAJudgeQuotesAnAmount_ThenItKeepsThePrecisionItWasQuotedWith(
        self, quoted_text: str, expected_amount_and_exponent: tuple[Decimal, int]
    ) -> None:
        # Act
        actual_amount: Decimal | None = AmountTextProcessor.parse_quoted_amount(quoted_text)

        # Assert
        actual_amount_and_exponent: tuple[Decimal | None, int | str | None] = (
            actual_amount,
            None if actual_amount is None else actual_amount.as_tuple().exponent,
        )
        assert actual_amount_and_exponent == expected_amount_and_exponent, (
            f"expected amount and exponent {expected_amount_and_exponent} for {quoted_text!r}; actual {actual_amount_and_exponent}"
        )
