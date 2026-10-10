import json
import secrets
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Final, cast

from acceptance_support.random_data_generator import RandomDataGenerator
from acceptance_support.sample_eval_suite_builder import (
    CASE_DIRECTORY,
    EXPECTED_STATUS,
    STATUS_FACT_NAME,
    TOTAL_FACT_NAME,
    SampleEvalSuite,
    SampleEvalSuiteBuilder,
)

CASE_REFERENCE_LEDGER_FILE: Final[str] = f"{CASE_DIRECTORY}/reference_ledger.json"
# Entry amounts grow by a factor of four, so no two different combinations of entries add up to the same difference
# and every scripted wrong total has exactly one explanation.
AMOUNT_GROWTH_FACTOR: Final[int] = 4
SMALLEST_AMOUNT_CENTS: Final[int] = 1_000
AMOUNT_SPREAD_CENTS: Final[int] = 1_000
CENTS_PER_DOLLAR: Final[Decimal] = Decimal(100)
MEMBER_ENTRY_COUNT: Final[int] = 3

type JsonObject = dict[str, object]


@dataclass(frozen=True)
class SampleLedgerEntry:
    line_number: int
    source_text: str
    amount: Decimal
    category: str


@dataclass(frozen=True)
class SampleReferenceLedger:
    """The total fact's ledger: member entries that add up to the expected total, and one entry of another category."""

    category: str
    period: str
    member_entries: tuple[SampleLedgerEntry, ...]
    other_category_entry: SampleLedgerEntry
    total_amount: Decimal


class SampleReferenceLedgerBuilder:
    """Adds a reference ledger to a sample eval suite and makes the expected total the ledger's total."""

    @staticmethod
    def write_sample_reference_ledger(sample_eval_suite: SampleEvalSuite) -> SampleReferenceLedger:
        category: str = f"category-{RandomDataGenerator.create_random_word()}"
        period: str = f"period-{RandomDataGenerator.create_random_word()}"
        member_entries: tuple[SampleLedgerEntry, ...] = tuple(
            SampleReferenceLedgerBuilder._create_entry(line_number=entry_index + 1, magnitude_index=2 * entry_index, category=category)
            for entry_index in range(MEMBER_ENTRY_COUNT)
        )
        other_category_entry: SampleLedgerEntry = SampleReferenceLedgerBuilder._create_entry(
            line_number=MEMBER_ENTRY_COUNT + 1, magnitude_index=1, category=f"category-{RandomDataGenerator.create_random_word()}"
        )
        total_amount: Decimal = sum((member_entry.amount for member_entry in member_entries), Decimal(0))
        SampleReferenceLedgerBuilder.write_reference_ledger_document(
            sample_eval_suite.eval_suite_directory,
            {
                "entries": [
                    SampleReferenceLedgerBuilder._create_entry_object(ledger_entry, period)
                    for ledger_entry in (*member_entries, other_category_entry)
                ],
                "amount_facts": {TOTAL_FACT_NAME: {"category": category, "period": period}},
            },
        )
        SampleEvalSuiteBuilder.write_expected_facts(
            sample_eval_suite.eval_suite_directory, {TOTAL_FACT_NAME: [str(total_amount)], STATUS_FACT_NAME: [EXPECTED_STATUS]}
        )
        return SampleReferenceLedger(
            category=category, period=period, member_entries=member_entries, other_category_entry=other_category_entry, total_amount=total_amount
        )

    @staticmethod
    def write_reference_ledger_document(eval_suite_directory: Path, reference_ledger_document: JsonObject) -> None:
        """Writes the ledger file and names it in the case's definition."""
        (eval_suite_directory / CASE_REFERENCE_LEDGER_FILE).write_text(json.dumps(reference_ledger_document, indent=2), encoding="utf-8")
        eval_suite_definition: JsonObject = cast(JsonObject, json.loads((eval_suite_directory / "eval_suite.json").read_text(encoding="utf-8")))
        case_objects: list[JsonObject] = cast(list[JsonObject], eval_suite_definition["cases"])
        case_objects[0]["reference_ledger_file"] = CASE_REFERENCE_LEDGER_FILE
        SampleEvalSuiteBuilder.write_eval_suite_definition(eval_suite_directory, eval_suite_definition)

    @staticmethod
    def _create_entry(*, line_number: int, magnitude_index: int, category: str) -> SampleLedgerEntry:
        amount: Decimal = (
            Decimal(SMALLEST_AMOUNT_CENTS * AMOUNT_GROWTH_FACTOR**magnitude_index + secrets.randbelow(AMOUNT_SPREAD_CENTS)) / CENTS_PER_DOLLAR
        )
        return SampleLedgerEntry(
            line_number=line_number,
            source_text=f"{RandomDataGenerator.create_random_word()} ${amount}",
            amount=amount,
            category=category,
        )

    @staticmethod
    def _create_entry_object(ledger_entry: SampleLedgerEntry, period: str) -> JsonObject:
        return {
            "line_number": ledger_entry.line_number,
            "source_text": ledger_entry.source_text,
            "period": period,
            "amount": str(ledger_entry.amount),
            "category": ledger_entry.category,
            "alternative_categories": [],
            "policy_name": None,
            "is_counted": True,
            "note": None,
        }
