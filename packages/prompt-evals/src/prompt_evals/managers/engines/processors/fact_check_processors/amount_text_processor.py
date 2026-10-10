import re
from decimal import Decimal, InvalidOperation
from typing import Final, final

# Amounts of 10^15 or more are extraction noise. The limit is checked on the exponent alone, because even abs() on a
# number like 1e1000000 raises decimal.Overflow under the default context.
AMOUNT_MAXIMUM_ADJUSTED_EXPONENT: Final[int] = 14
AMOUNT_FORMATTING_CHARACTERS: Final[tuple[str, ...]] = ("$", ",", " ")
# Models sometimes write a negative amount with the Unicode minus sign.
UNICODE_MINUS_SIGN: Final[str] = "\N{MINUS SIGN}"
AMOUNT_TEXT_PATTERN: Final[re.Pattern[str]] = re.compile(rf"[-{UNICODE_MINUS_SIGN}]?\s*\$?\s*\d[\d,]*(?:\.\d+)?")


@final
class AmountTextProcessor:
    """Reads amounts from text a model wrote."""

    @staticmethod
    def parse_reported_amount(amount_text: str) -> Decimal | None:
        """The amount in a reported value such as "$1,631.82", also when written with the Unicode minus sign; None when the value
        is not a plausible amount."""
        normalized_amount_text: str = amount_text.replace(UNICODE_MINUS_SIGN, "-")
        for formatting_character in AMOUNT_FORMATTING_CHARACTERS:
            normalized_amount_text = normalized_amount_text.replace(formatting_character, "")
        try:
            parsed_amount: Decimal = Decimal(normalized_amount_text)
        except InvalidOperation:
            return None
        if not parsed_amount.is_finite() or parsed_amount.adjusted() > AMOUNT_MAXIMUM_ADJUSTED_EXPONENT:
            return None
        return parsed_amount

    @staticmethod
    def parse_quoted_amount(amount_text: str) -> Decimal | None:
        """The first amount in text a model wrote, such as "$1,068.35" or "about $2,996"; None when there is none.
        The amount keeps the precision it was quoted with, so "about $2,996" is a whole-dollar amount."""
        amount_match: re.Match[str] | None = AMOUNT_TEXT_PATTERN.search(amount_text)
        if amount_match is None:
            return None
        normalized_amount_text: str = re.sub(r"[\s$,]", "", amount_match.group()).replace(UNICODE_MINUS_SIGN, "-")
        try:
            return Decimal(normalized_amount_text)
        except InvalidOperation:
            return None
