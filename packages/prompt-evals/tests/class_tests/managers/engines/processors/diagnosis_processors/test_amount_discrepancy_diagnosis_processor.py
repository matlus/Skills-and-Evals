import secrets
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

import pytest
from acceptance_support.random_data_generator import RandomDataGenerator

from prompt_evals.managers.data_managers.processors.reference_ledger_totals_processor import ReferenceLedgerTotalsProcessor
from prompt_evals.managers.engines.processors.diagnosis_processors.amount_discrepancy_diagnosis_processor import AmountDiscrepancyDiagnosisProcessor
from prompt_evals.managers.models.diagnosis_models import AmountDiscrepancyDiagnosis, EntryMistakeKind
from prompt_evals.managers.models.reference_ledger_models import (
    AmountFactLedgerBucket,
    LedgerBucket,
    LedgerBucketTotals,
    LedgerEntry,
    ReferenceLedger,
)

# Entry amounts grow by a factor of four, so no two different combinations of entries (each left out, counted in, or
# sign-reversed) add up to the same difference: every test difference has exactly one explanation.
AMOUNT_GROWTH_FACTOR: Final[int] = 4
SMALLEST_AMOUNT_CENTS: Final[int] = 1_000
AMOUNT_SPREAD_CENTS: Final[int] = 1_000
CENTS_PER_DOLLAR: Final[Decimal] = Decimal(100)
WHOLE_DOLLAR: Final[Decimal] = Decimal(1)


@dataclass(frozen=True)
class SampleLedger:
    """A small ledger: the bucket under test with its totals, its member entries, and entries a mistake could bring in."""

    reference_ledger: ReferenceLedger
    ledger_bucket_totals: LedgerBucketTotals
    member_entries: tuple[LedgerEntry, ...]
    other_category_entry: LedgerEntry
    other_period_entry: LedgerEntry
    uncounted_entry: LedgerEntry
    refund_entry: LedgerEntry
    policy_entry: LedgerEntry
    policy_name: str


@dataclass(frozen=True)
class ExplanationSummary:
    """How many simplest explanations a diagnosis found, and the entry mistakes of the first one."""

    explanation_count: int
    first_explanation_mistakes: tuple[tuple[EntryMistakeKind, int], ...]


def create_amount(magnitude_index: int) -> Decimal:
    cents: int = SMALLEST_AMOUNT_CENTS * AMOUNT_GROWTH_FACTOR**magnitude_index + secrets.randbelow(AMOUNT_SPREAD_CENTS)
    return Decimal(cents) / CENTS_PER_DOLLAR


def create_ledger_entry(
    line_number: int,
    period: str,
    amount: Decimal,
    category: str,
    *,
    alternative_categories: tuple[str, ...] = (),
    policy_name: str | None = None,
    is_counted: bool = True,
    note: str | None = None,
) -> LedgerEntry:
    return LedgerEntry(
        line_number=line_number,
        source_text=f"{RandomDataGenerator.create_random_word()} ${amount}",
        period=period,
        amount=amount,
        category=category,
        alternative_categories=alternative_categories,
        policy_name=policy_name,
        is_counted=is_counted,
        note=note,
    )


def create_sample_ledger() -> SampleLedger:
    category: str = f"category-{RandomDataGenerator.create_random_word()}"
    other_category: str = f"category-{RandomDataGenerator.create_random_word()}"
    period: str = f"period-{RandomDataGenerator.create_random_word()}"
    other_period: str = f"period-{RandomDataGenerator.create_random_word()}"
    policy_name: str = RandomDataGenerator.create_random_sentence()
    fact_name: str = f"fact-{RandomDataGenerator.create_random_word()}"
    member_entries: tuple[LedgerEntry, ...] = (
        create_ledger_entry(10, period, create_amount(0), category),
        create_ledger_entry(11, period, create_amount(2), category),
        create_ledger_entry(12, period, create_amount(4), category),
    )
    refund_entry: LedgerEntry = create_ledger_entry(13, period, -create_amount(1), category)
    other_category_entry: LedgerEntry = create_ledger_entry(20, period, create_amount(3), other_category)
    other_period_entry: LedgerEntry = create_ledger_entry(21, other_period, create_amount(5), category)
    uncounted_entry: LedgerEntry = create_ledger_entry(
        22, period, create_amount(6), category, is_counted=False, note=f"likely duplicate {RandomDataGenerator.create_random_word()}"
    )
    policy_entry: LedgerEntry = create_ledger_entry(
        23, period, create_amount(7), other_category, alternative_categories=(category,), policy_name=policy_name
    )
    reference_ledger: ReferenceLedger = ReferenceLedgerTotalsProcessor.total_reference_ledger(
        (*member_entries, refund_entry, other_category_entry, other_period_entry, uncounted_entry, policy_entry),
        (AmountFactLedgerBucket(fact_name=fact_name, ledger_bucket=LedgerBucket(category=category, period=period)),),
    )
    return SampleLedger(
        reference_ledger=reference_ledger,
        ledger_bucket_totals=reference_ledger.ledger_bucket_totals_by_fact_name[fact_name],
        member_entries=(*member_entries, refund_entry),
        other_category_entry=other_category_entry,
        other_period_entry=other_period_entry,
        uncounted_entry=uncounted_entry,
        refund_entry=refund_entry,
        policy_entry=policy_entry,
        policy_name=policy_name,
    )


def sum_amounts(ledger_entries: tuple[LedgerEntry, ...]) -> Decimal:
    return sum((ledger_entry.amount for ledger_entry in ledger_entries), Decimal(0))


def summarize_explanations(amount_discrepancy_diagnosis: AmountDiscrepancyDiagnosis) -> ExplanationSummary:
    if not amount_discrepancy_diagnosis.discrepancy_explanations:
        return ExplanationSummary(explanation_count=0, first_explanation_mistakes=())
    return ExplanationSummary(
        explanation_count=len(amount_discrepancy_diagnosis.discrepancy_explanations),
        first_explanation_mistakes=tuple(
            (entry_mistake.entry_mistake_kind, entry_mistake.ledger_entry.line_number)
            for entry_mistake in amount_discrepancy_diagnosis.discrepancy_explanations[0].entry_mistakes
        ),
    )


def read_ledger_bucket(ledger_bucket_totals: LedgerBucketTotals | None) -> LedgerBucket | None:
    return None if ledger_bucket_totals is None else ledger_bucket_totals.ledger_bucket


@pytest.mark.class_test
class TestAmountDiscrepancyDiagnosisProcessor:
    def test_DiagnoseReportedAmount_WhenOneReferenceEntryIsLeftOut_ThenTheDiagnosisNamesThatEntry(self) -> None:
        # Arrange
        sample_ledger: SampleLedger = create_sample_ledger()
        left_out_ledger_entry: LedgerEntry = sample_ledger.member_entries[1]
        reported_amount: Decimal = sum_amounts(sample_ledger.member_entries) - left_out_ledger_entry.amount
        expected_explanation_summary: ExplanationSummary = ExplanationSummary(
            explanation_count=1, first_explanation_mistakes=((EntryMistakeKind.LEFT_OUT, left_out_ledger_entry.line_number),)
        )
        expected_description_phrase: str = f'left out line {left_out_ledger_entry.line_number} "{left_out_ledger_entry.source_text}"'

        # Act
        actual_diagnosis: AmountDiscrepancyDiagnosis = AmountDiscrepancyDiagnosisProcessor.diagnose_reported_amount(
            sample_ledger.reference_ledger.ledger_entries, sample_ledger.ledger_bucket_totals, reported_amount
        )

        # Assert
        actual_explanation_summary: ExplanationSummary = summarize_explanations(actual_diagnosis)
        assert (actual_explanation_summary, expected_description_phrase in actual_diagnosis.cause_description) == (
            expected_explanation_summary,
            True,
        ), (
            f"expected {expected_explanation_summary} described with {expected_description_phrase!r}; "
            f"actual {actual_explanation_summary}: {actual_diagnosis.cause_description!r}"
        )

    def test_DiagnoseReportedAmount_WhenAnEntryOfAnotherCategoryIsCountedIn_ThenTheDiagnosisNamesItAndWhereTheReferencePutsIt(self) -> None:
        # Arrange
        sample_ledger: SampleLedger = create_sample_ledger()
        reported_amount: Decimal = sum_amounts(sample_ledger.member_entries) + sample_ledger.other_category_entry.amount
        expected_explanation_summary: ExplanationSummary = ExplanationSummary(
            explanation_count=1,
            first_explanation_mistakes=((EntryMistakeKind.WRONGLY_INCLUDED, sample_ledger.other_category_entry.line_number),),
        )
        expected_description_phrase: str = f"which the reference puts in {sample_ledger.other_category_entry.category}"

        # Act
        actual_diagnosis: AmountDiscrepancyDiagnosis = AmountDiscrepancyDiagnosisProcessor.diagnose_reported_amount(
            sample_ledger.reference_ledger.ledger_entries, sample_ledger.ledger_bucket_totals, reported_amount
        )

        # Assert
        actual_explanation_summary: ExplanationSummary = summarize_explanations(actual_diagnosis)
        assert (actual_explanation_summary, expected_description_phrase in actual_diagnosis.cause_description) == (
            expected_explanation_summary,
            True,
        ), (
            f"expected {expected_explanation_summary} described with {expected_description_phrase!r}; "
            f"actual {actual_explanation_summary}: {actual_diagnosis.cause_description!r}"
        )

    def test_DiagnoseReportedAmount_WhenARefundIsCountedAsASpend_ThenTheDiagnosisSaysItsSignWasReversed(self) -> None:
        # Arrange
        sample_ledger: SampleLedger = create_sample_ledger()
        reported_amount: Decimal = sum_amounts(sample_ledger.member_entries) - 2 * sample_ledger.refund_entry.amount
        expected_explanation_summary: ExplanationSummary = ExplanationSummary(
            explanation_count=1, first_explanation_mistakes=((EntryMistakeKind.SIGN_REVERSED, sample_ledger.refund_entry.line_number),)
        )
        expected_description_phrase: str = "with its sign reversed"

        # Act
        actual_diagnosis: AmountDiscrepancyDiagnosis = AmountDiscrepancyDiagnosisProcessor.diagnose_reported_amount(
            sample_ledger.reference_ledger.ledger_entries, sample_ledger.ledger_bucket_totals, reported_amount
        )

        # Assert
        actual_explanation_summary: ExplanationSummary = summarize_explanations(actual_diagnosis)
        assert (actual_explanation_summary, expected_description_phrase in actual_diagnosis.cause_description) == (
            expected_explanation_summary,
            True,
        ), (
            f"expected {expected_explanation_summary} described with {expected_description_phrase!r}; "
            f"actual {actual_explanation_summary}: {actual_diagnosis.cause_description!r}"
        )

    def test_DiagnoseReportedAmount_WhenTheLikelyDuplicateIsCounted_ThenTheDiagnosisSaysTheReferenceDoesNotCountIt(self) -> None:
        # Arrange
        sample_ledger: SampleLedger = create_sample_ledger()
        reported_amount: Decimal = sum_amounts(sample_ledger.member_entries) + sample_ledger.uncounted_entry.amount
        expected_explanation_summary: ExplanationSummary = ExplanationSummary(
            explanation_count=1,
            first_explanation_mistakes=((EntryMistakeKind.WRONGLY_INCLUDED, sample_ledger.uncounted_entry.line_number),),
        )
        expected_description_phrase: str = f"which the reference does not count ({sample_ledger.uncounted_entry.note})"

        # Act
        actual_diagnosis: AmountDiscrepancyDiagnosis = AmountDiscrepancyDiagnosisProcessor.diagnose_reported_amount(
            sample_ledger.reference_ledger.ledger_entries, sample_ledger.ledger_bucket_totals, reported_amount
        )

        # Assert
        actual_explanation_summary: ExplanationSummary = summarize_explanations(actual_diagnosis)
        assert (actual_explanation_summary, expected_description_phrase in actual_diagnosis.cause_description) == (
            expected_explanation_summary,
            True,
        ), (
            f"expected {expected_explanation_summary} described with {expected_description_phrase!r}; "
            f"actual {actual_explanation_summary}: {actual_diagnosis.cause_description!r}"
        )

    def test_DiagnoseReportedAmount_WhenAnEntryFromAnotherPeriodIsCounted_ThenTheDiagnosisNamesThePeriodTheReferencePutsItIn(self) -> None:
        # Arrange
        sample_ledger: SampleLedger = create_sample_ledger()
        reported_amount: Decimal = sum_amounts(sample_ledger.member_entries) + sample_ledger.other_period_entry.amount
        expected_explanation_summary: ExplanationSummary = ExplanationSummary(
            explanation_count=1,
            first_explanation_mistakes=((EntryMistakeKind.WRONGLY_INCLUDED, sample_ledger.other_period_entry.line_number),),
        )
        expected_description_phrase: str = f"which the reference puts in {sample_ledger.other_period_entry.period}"

        # Act
        actual_diagnosis: AmountDiscrepancyDiagnosis = AmountDiscrepancyDiagnosisProcessor.diagnose_reported_amount(
            sample_ledger.reference_ledger.ledger_entries, sample_ledger.ledger_bucket_totals, reported_amount
        )

        # Assert
        actual_explanation_summary: ExplanationSummary = summarize_explanations(actual_diagnosis)
        assert (actual_explanation_summary, expected_description_phrase in actual_diagnosis.cause_description) == (
            expected_explanation_summary,
            True,
        ), (
            f"expected {expected_explanation_summary} described with {expected_description_phrase!r}; "
            f"actual {actual_explanation_summary}: {actual_diagnosis.cause_description!r}"
        )

    def test_DiagnoseReportedAmount_WhenThreeReferenceEntriesAreLeftOut_ThenTheDiagnosisNamesAllThree(self) -> None:
        # Arrange
        sample_ledger: SampleLedger = create_sample_ledger()
        left_out_ledger_entries: tuple[LedgerEntry, ...] = sample_ledger.member_entries[:3]
        reported_amount: Decimal = sum_amounts(sample_ledger.member_entries) - sum_amounts(left_out_ledger_entries)
        expected_explanation_summary: ExplanationSummary = ExplanationSummary(
            explanation_count=1,
            first_explanation_mistakes=tuple(
                (EntryMistakeKind.LEFT_OUT, left_out_ledger_entry.line_number) for left_out_ledger_entry in left_out_ledger_entries
            ),
        )

        # Act
        actual_diagnosis: AmountDiscrepancyDiagnosis = AmountDiscrepancyDiagnosisProcessor.diagnose_reported_amount(
            sample_ledger.reference_ledger.ledger_entries, sample_ledger.ledger_bucket_totals, reported_amount
        )

        # Assert
        actual_explanation_summary: ExplanationSummary = summarize_explanations(actual_diagnosis)
        assert actual_explanation_summary == expected_explanation_summary, (
            f"expected {expected_explanation_summary}; actual {actual_explanation_summary}: {actual_diagnosis.cause_description!r}"
        )

    def test_DiagnoseReportedAmount_WhenAnAcceptedPolicyAndOneMistakeExplainTheTotal_ThenThePolicyIsAppliedAndOnlyTheMistakeIsNamed(self) -> None:
        # Arrange
        sample_ledger: SampleLedger = create_sample_ledger()
        policy_total: Decimal = sum_amounts(sample_ledger.member_entries) + sample_ledger.policy_entry.amount
        reported_amount: Decimal = policy_total + sample_ledger.other_category_entry.amount
        expected_outcome: tuple[object, ...] = (
            (sample_ledger.policy_name,),
            policy_total,
            ExplanationSummary(
                explanation_count=1,
                first_explanation_mistakes=((EntryMistakeKind.WRONGLY_INCLUDED, sample_ledger.other_category_entry.line_number),),
            ),
        )

        # Act
        actual_diagnosis: AmountDiscrepancyDiagnosis = AmountDiscrepancyDiagnosisProcessor.diagnose_reported_amount(
            sample_ledger.reference_ledger.ledger_entries, sample_ledger.ledger_bucket_totals, reported_amount
        )

        # Assert
        actual_outcome: tuple[object, ...] = (
            actual_diagnosis.accepted_policy_names,
            actual_diagnosis.reference_amount,
            summarize_explanations(actual_diagnosis),
        )
        assert actual_outcome == expected_outcome, f"expected {expected_outcome}; actual {actual_outcome}: {actual_diagnosis.cause_description!r}"

    def test_DiagnoseReportedAmount_WhenTheAmountMatchesAnAcceptedPolicy_ThenNoMistakeIsNamedAndThePolicyIsGiven(self) -> None:
        # Arrange
        sample_ledger: SampleLedger = create_sample_ledger()
        reported_amount: Decimal = sum_amounts(sample_ledger.member_entries) + sample_ledger.policy_entry.amount
        expected_outcome: tuple[object, ...] = ((sample_ledger.policy_name,), (), True)

        # Act
        actual_diagnosis: AmountDiscrepancyDiagnosis = AmountDiscrepancyDiagnosisProcessor.diagnose_reported_amount(
            sample_ledger.reference_ledger.ledger_entries, sample_ledger.ledger_bucket_totals, reported_amount
        )

        # Assert
        actual_outcome: tuple[object, ...] = (
            actual_diagnosis.accepted_policy_names,
            actual_diagnosis.discrepancy_explanations,
            "matches the reference under an accepted policy" in actual_diagnosis.cause_description,
        )
        assert actual_outcome == expected_outcome, f"expected {expected_outcome}; actual {actual_outcome}: {actual_diagnosis.cause_description!r}"

    def test_DiagnoseReportedAmount_WhenNoFewEntriesExplainTheDifference_ThenTheDiagnosisSaysSoAgainstTheReferenceTotal(self) -> None:
        # Arrange
        sample_ledger: SampleLedger = create_sample_ledger()
        reference_total: Decimal = sum_amounts(sample_ledger.member_entries)
        # Every entry is at least 10.00, so a difference of a few cents is no combination of entries.
        unexplainable_difference: Decimal = Decimal(secrets.randbelow(90) + 5) / CENTS_PER_DOLLAR
        reported_amount: Decimal = reference_total + unexplainable_difference
        expected_outcome: tuple[object, ...] = ((), reference_total, True)

        # Act
        actual_diagnosis: AmountDiscrepancyDiagnosis = AmountDiscrepancyDiagnosisProcessor.diagnose_reported_amount(
            sample_ledger.reference_ledger.ledger_entries, sample_ledger.ledger_bucket_totals, reported_amount
        )

        # Assert
        actual_outcome: tuple[object, ...] = (
            actual_diagnosis.discrepancy_explanations,
            actual_diagnosis.reference_amount,
            "no combination of up to 3 entries explains" in actual_diagnosis.cause_description,
        )
        assert actual_outcome == expected_outcome, f"expected {expected_outcome}; actual {actual_outcome}: {actual_diagnosis.cause_description!r}"

    @pytest.mark.parametrize("is_rounded", [False, True], ids=["exact", "whole-dollar"])
    def test_FindLedgerBucketWithReferenceAmount_WhenAJudgeQuotesABucketTotal_ThenThatBucketIsFound(self, *, is_rounded: bool) -> None:
        # Arrange
        sample_ledger: SampleLedger = create_sample_ledger()
        reference_total: Decimal = sum_amounts(sample_ledger.member_entries)
        # A whole-dollar quote is rounded the way the processor reads one: half up.
        reference_amount: Decimal = reference_total.quantize(WHOLE_DOLLAR, rounding=ROUND_HALF_UP) if is_rounded else reference_total
        expected_ledger_bucket: LedgerBucket = sample_ledger.ledger_bucket_totals.ledger_bucket

        # Act
        actual_ledger_bucket_totals: LedgerBucketTotals | None = AmountDiscrepancyDiagnosisProcessor.find_ledger_bucket_with_reference_amount(
            sample_ledger.reference_ledger.ledger_bucket_totals, reference_amount, RandomDataGenerator.create_random_sentence()
        )

        # Assert
        actual_ledger_bucket: LedgerBucket | None = read_ledger_bucket(actual_ledger_bucket_totals)
        assert actual_ledger_bucket == expected_ledger_bucket, (
            f"expected {expected_ledger_bucket}; actual {actual_ledger_bucket} for {reference_amount}"
        )

    def test_FindLedgerBucketWithReferenceAmount_WhenTwoCategoriesShareTheTotal_ThenTheCategoryTheDescriptionNamesIsChosen(self) -> None:
        # Arrange
        period: str = f"period-{RandomDataGenerator.create_random_word()}"
        shared_amount: Decimal = create_amount(1)
        first_category: str = f"category-{RandomDataGenerator.create_random_word()}"
        second_category: str = f"category-{RandomDataGenerator.create_random_word()}"
        reference_ledger: ReferenceLedger = ReferenceLedgerTotalsProcessor.total_reference_ledger(
            (
                create_ledger_entry(1, period, shared_amount, first_category),
                create_ledger_entry(2, period, shared_amount, second_category),
            ),
            (),
        )
        expected_outcome: tuple[LedgerBucket | None, LedgerBucket | None] = (None, LedgerBucket(category=second_category, period=period))

        # Act
        actual_undescribed_ledger_bucket_totals: LedgerBucketTotals | None = (
            AmountDiscrepancyDiagnosisProcessor.find_ledger_bucket_with_reference_amount(
                reference_ledger.ledger_bucket_totals, shared_amount, RandomDataGenerator.create_random_sentence()
            )
        )
        actual_described_ledger_bucket_totals: LedgerBucketTotals | None = (
            AmountDiscrepancyDiagnosisProcessor.find_ledger_bucket_with_reference_amount(
                reference_ledger.ledger_bucket_totals, shared_amount, f"{second_category.upper()} in {period}"
            )
        )

        # Assert
        actual_outcome: tuple[LedgerBucket | None, LedgerBucket | None] = (
            read_ledger_bucket(actual_undescribed_ledger_bucket_totals),
            read_ledger_bucket(actual_described_ledger_bucket_totals),
        )
        assert actual_outcome == expected_outcome, f"expected (no description, naming description) {expected_outcome}; actual {actual_outcome}"

    def test_FindLedgerBucketWithReferenceAmount_WhenTheQuotedReferenceIsZero_ThenNoBucketIsChosen(self) -> None:
        # Arrange
        sample_ledger: SampleLedger = create_sample_ledger()

        # Act
        actual_ledger_bucket_totals: LedgerBucketTotals | None = AmountDiscrepancyDiagnosisProcessor.find_ledger_bucket_with_reference_amount(
            sample_ledger.reference_ledger.ledger_bucket_totals,
            Decimal(0),
            f"{sample_ledger.ledger_bucket_totals.ledger_bucket.category} {RandomDataGenerator.create_random_sentence()}",
        )

        # Assert
        assert actual_ledger_bucket_totals is None, f"expected no bucket for a zero reference; actual {actual_ledger_bucket_totals}"
