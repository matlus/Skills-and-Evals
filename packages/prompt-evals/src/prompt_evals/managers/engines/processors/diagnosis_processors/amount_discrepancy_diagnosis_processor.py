from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from itertools import combinations
from typing import Final, final

from prompt_evals.managers.models.diagnosis_models import AmountDiscrepancyDiagnosis, DiscrepancyExplanation, EntryMistake, EntryMistakeKind
from prompt_evals.managers.models.reference_ledger_models import LedgerBucket, LedgerBucketComposition, LedgerBucketTotals, LedgerEntry

# Answers round to the cent, so a difference within one cent is no difference.
AMOUNT_TOLERANCE: Final[Decimal] = Decimal("0.01")
MAXIMUM_MISTAKE_COUNT: Final[int] = 3
# Among dozens of entries, two or three arbitrary amounts can add up to almost any difference by coincidence. The search
# therefore considers every entry only up to these sizes and beyond them only plausible mistakes (see _is_plausible).
FULL_SEARCH_MISTAKE_COUNT_FOR_ONE_PERIOD: Final[int] = 2
FULL_SEARCH_MISTAKE_COUNT_FOR_EVERY_PERIOD: Final[int] = 1
MAXIMUM_EXPLANATION_COUNT: Final[int] = 3
CENT: Final[Decimal] = Decimal("0.01")
WHOLE_DOLLAR: Final[Decimal] = Decimal(1)
WHOLE_NUMBER_EXPONENT: Final[int] = 0


@dataclass(frozen=True)
class CandidateMistake:
    entry_mistake: EntryMistake
    is_plausible: bool


@dataclass(frozen=True)
class CompositionFit:
    ledger_bucket_composition: LedgerBucketComposition
    discrepancy_explanations: tuple[DiscrepancyExplanation, ...]
    mistake_count: int


@final
class AmountDiscrepancyDiagnosisProcessor:
    """Traces a wrong total to the ledger entries that make the difference, the way a person reconciling it by hand would:
    which reference entries were left out, which other entries were counted in, and which refund kept the wrong sign.

    It first applies any accepted policy that brings the reference closer to the answer, then looks for the fewest
    entry mistakes whose effects add up exactly to what remains.
    """

    @staticmethod
    def diagnose_reported_amount(
        ledger_entries: tuple[LedgerEntry, ...], ledger_bucket_totals: LedgerBucketTotals, reported_amount: Decimal
    ) -> AmountDiscrepancyDiagnosis:
        ledger_bucket: LedgerBucket = ledger_bucket_totals.ledger_bucket
        ledger_bucket_compositions: tuple[LedgerBucketComposition, ...] = ledger_bucket_totals.ledger_bucket_compositions
        composition_fit: CompositionFit | None = AmountDiscrepancyDiagnosisProcessor._find_simplest_fit(
            ledger_entries, ledger_bucket_compositions, reported_amount
        )
        # Without a fit, the difference is reported against the key's own total.
        explained_ledger_bucket_composition: LedgerBucketComposition = (
            ledger_bucket_compositions[0] if composition_fit is None else composition_fit.ledger_bucket_composition
        )
        discrepancy_explanations: tuple[DiscrepancyExplanation, ...] = () if composition_fit is None else composition_fit.discrepancy_explanations
        return AmountDiscrepancyDiagnosis(
            ledger_bucket=ledger_bucket,
            reported_amount=reported_amount,
            reference_amount=explained_ledger_bucket_composition.total_amount,
            accepted_policy_names=explained_ledger_bucket_composition.accepted_policy_names,
            discrepancy_explanations=discrepancy_explanations,
            cause_summary=AmountDiscrepancyDiagnosisProcessor._summarize_cause(ledger_bucket, explained_ledger_bucket_composition, composition_fit),
            cause_description=AmountDiscrepancyDiagnosisProcessor._describe_cause(
                ledger_bucket, reported_amount, explained_ledger_bucket_composition, composition_fit
            ),
        )

    @staticmethod
    def find_ledger_bucket_with_reference_amount(
        all_ledger_bucket_totals: Iterable[LedgerBucketTotals], reference_amount: Decimal, amount_description: str
    ) -> LedgerBucketTotals | None:
        """The one bucket whose total, under the key's policy or an accepted one, is the amount a judge quoted as the reference.
        A whole-dollar quote such as "about $2,996" matches a total that rounds to it.

        None when no bucket or several unrelated buckets match: tracing against a guessed bucket would name a coincidence.
        Buckets made of the same entries (a category with entries in one period only) are one total. When distinct buckets
        share the amount, the one whose category the judge's description names is chosen.
        """
        matching_ledger_bucket_totals: list[LedgerBucketTotals] = AmountDiscrepancyDiagnosisProcessor._collect_buckets_matching_quote(
            all_ledger_bucket_totals, reference_amount
        )
        return AmountDiscrepancyDiagnosisProcessor._select_bucket_named_by_description(matching_ledger_bucket_totals, amount_description)

    @staticmethod
    def _collect_buckets_matching_quote(
        all_ledger_bucket_totals: Iterable[LedgerBucketTotals], reference_amount: Decimal
    ) -> list[LedgerBucketTotals]:
        is_matching_total: Callable[[Decimal, Decimal], bool] = (
            AmountDiscrepancyDiagnosisProcessor._rounds_to_whole_dollar_amount
            if reference_amount.as_tuple().exponent == WHOLE_NUMBER_EXPONENT
            else AmountDiscrepancyDiagnosisProcessor._is_same_amount
        )
        matching_ledger_bucket_totals_by_member_lines: dict[frozenset[int], LedgerBucketTotals] = {}
        # Buckets are listed period by period before the whole-period ones, so the most specific of equal totals is kept.
        for ledger_bucket_totals in all_ledger_bucket_totals:
            for ledger_bucket_composition in ledger_bucket_totals.ledger_bucket_compositions:
                # An empty bucket totals zero in many places at once, and every entry of a nonzero answer would be a candidate.
                if ledger_bucket_composition.member_entries and is_matching_total(ledger_bucket_composition.total_amount, reference_amount):
                    member_lines: frozenset[int] = frozenset(member_entry.line_number for member_entry in ledger_bucket_composition.member_entries)
                    matching_ledger_bucket_totals_by_member_lines.setdefault(member_lines, ledger_bucket_totals)
        return list(
            {
                matching_ledger_bucket_totals.ledger_bucket: matching_ledger_bucket_totals
                for matching_ledger_bucket_totals in matching_ledger_bucket_totals_by_member_lines.values()
            }.values()
        )

    @staticmethod
    def _select_bucket_named_by_description(
        matching_ledger_bucket_totals: list[LedgerBucketTotals], amount_description: str
    ) -> LedgerBucketTotals | None:
        named_ledger_bucket_totals: list[LedgerBucketTotals] = (
            matching_ledger_bucket_totals
            if len(matching_ledger_bucket_totals) <= 1
            else [
                ledger_bucket_totals
                for ledger_bucket_totals in matching_ledger_bucket_totals
                if ledger_bucket_totals.ledger_bucket.category.casefold() in amount_description.casefold()
            ]
        )
        return named_ledger_bucket_totals[0] if len(named_ledger_bucket_totals) == 1 else None

    @staticmethod
    def _is_same_amount(left_amount: Decimal, right_amount: Decimal) -> bool:
        return abs(left_amount - right_amount) <= AMOUNT_TOLERANCE

    @staticmethod
    def _rounds_to_whole_dollar_amount(total_amount: Decimal, whole_dollar_amount: Decimal) -> bool:
        return total_amount.quantize(WHOLE_DOLLAR, rounding=ROUND_HALF_UP) == whole_dollar_amount

    @staticmethod
    def _find_simplest_fit(
        ledger_entries: tuple[LedgerEntry, ...], ledger_bucket_compositions: Sequence[LedgerBucketComposition], reported_amount: Decimal
    ) -> CompositionFit | None:
        simplest_composition_fit: CompositionFit | None = None
        for ledger_bucket_composition in ledger_bucket_compositions:
            composition_fit: CompositionFit | None = AmountDiscrepancyDiagnosisProcessor._fit_composition(
                ledger_entries, ledger_bucket_composition, reported_amount
            )
            # Compositions come with the fewest policies first, so on a tie the explanation needing fewer policies stays.
            if composition_fit is not None and (
                simplest_composition_fit is None or composition_fit.mistake_count < simplest_composition_fit.mistake_count
            ):
                simplest_composition_fit = composition_fit
        return simplest_composition_fit

    @staticmethod
    def _fit_composition(
        ledger_entries: tuple[LedgerEntry, ...], ledger_bucket_composition: LedgerBucketComposition, reported_amount: Decimal
    ) -> CompositionFit | None:
        if AmountDiscrepancyDiagnosisProcessor._is_same_amount(reported_amount, ledger_bucket_composition.total_amount):
            return CompositionFit(ledger_bucket_composition=ledger_bucket_composition, discrepancy_explanations=(), mistake_count=0)
        difference: Decimal = reported_amount - ledger_bucket_composition.total_amount
        candidate_mistakes: list[CandidateMistake] = AmountDiscrepancyDiagnosisProcessor._list_candidate_mistakes(
            ledger_entries, ledger_bucket_composition
        )
        for mistake_count in range(1, MAXIMUM_MISTAKE_COUNT + 1):
            discrepancy_explanations: tuple[DiscrepancyExplanation, ...] = AmountDiscrepancyDiagnosisProcessor._find_explanations(
                AmountDiscrepancyDiagnosisProcessor._select_searched_mistakes(
                    candidate_mistakes, ledger_bucket_composition.ledger_bucket, mistake_count
                ),
                mistake_count,
                difference,
            )
            if discrepancy_explanations:
                return CompositionFit(
                    ledger_bucket_composition=ledger_bucket_composition,
                    discrepancy_explanations=discrepancy_explanations,
                    mistake_count=mistake_count,
                )
        return None

    @staticmethod
    def _select_searched_mistakes(
        candidate_mistakes: list[CandidateMistake], ledger_bucket: LedgerBucket, mistake_count: int
    ) -> list[CandidateMistake]:
        full_search_mistake_count: int = (
            FULL_SEARCH_MISTAKE_COUNT_FOR_EVERY_PERIOD if ledger_bucket.period is None else FULL_SEARCH_MISTAKE_COUNT_FOR_ONE_PERIOD
        )
        if mistake_count <= full_search_mistake_count:
            return candidate_mistakes
        return [candidate_mistake for candidate_mistake in candidate_mistakes if candidate_mistake.is_plausible]

    @staticmethod
    def _list_candidate_mistakes(
        ledger_entries: tuple[LedgerEntry, ...], ledger_bucket_composition: LedgerBucketComposition
    ) -> list[CandidateMistake]:
        ledger_bucket: LedgerBucket = ledger_bucket_composition.ledger_bucket
        member_line_numbers: set[int] = {member_entry.line_number for member_entry in ledger_bucket_composition.member_entries}
        candidate_mistakes: list[CandidateMistake] = []
        for member_entry in ledger_bucket_composition.member_entries:
            candidate_mistakes.append(
                AmountDiscrepancyDiagnosisProcessor._create_candidate(
                    member_entry, EntryMistakeKind.LEFT_OUT, -member_entry.amount, is_plausible=True
                )
            )
            if member_entry.amount < 0:
                candidate_mistakes.append(
                    AmountDiscrepancyDiagnosisProcessor._create_candidate(
                        member_entry, EntryMistakeKind.SIGN_REVERSED, -2 * member_entry.amount, is_plausible=True
                    )
                )
        candidate_mistakes.extend(
            AmountDiscrepancyDiagnosisProcessor._create_candidate(
                ledger_entry,
                EntryMistakeKind.WRONGLY_INCLUDED,
                ledger_entry.amount,
                is_plausible=AmountDiscrepancyDiagnosisProcessor._is_plausible(ledger_entry, ledger_bucket),
            )
            for ledger_entry in ledger_entries
            if ledger_entry.line_number not in member_line_numbers
            and (ledger_bucket.includes_period(ledger_entry.period) or ledger_entry.category == ledger_bucket.category)
        )
        return candidate_mistakes

    @staticmethod
    def _is_plausible(ledger_entry: LedgerEntry, ledger_bucket: LedgerBucket) -> bool:
        # Counting an entry the reference skips (a likely duplicate) or one an accepted policy could put here is a
        # recognizable slip. A same-category entry from another period, or an entry of an unrelated category, can fit by coincidence.
        return ledger_bucket.includes_period(ledger_entry.period) and (
            not ledger_entry.is_counted or ledger_bucket.category in ledger_entry.alternative_categories
        )

    @staticmethod
    def _create_candidate(
        ledger_entry: LedgerEntry, entry_mistake_kind: EntryMistakeKind, amount_effect: Decimal, *, is_plausible: bool
    ) -> CandidateMistake:
        return CandidateMistake(
            entry_mistake=EntryMistake(ledger_entry=ledger_entry, entry_mistake_kind=entry_mistake_kind, amount_effect=amount_effect),
            is_plausible=is_plausible,
        )

    @staticmethod
    def _find_explanations(
        candidate_mistakes: Sequence[CandidateMistake], mistake_count: int, difference: Decimal
    ) -> tuple[DiscrepancyExplanation, ...]:
        fitting_combinations: list[tuple[CandidateMistake, ...]] = [
            candidate_combination
            for candidate_combination in combinations(candidate_mistakes, mistake_count)
            if AmountDiscrepancyDiagnosisProcessor._has_distinct_entries(candidate_combination)
            and AmountDiscrepancyDiagnosisProcessor._is_same_amount(
                sum((candidate_mistake.entry_mistake.amount_effect for candidate_mistake in candidate_combination), Decimal(0)), difference
            )
        ]
        # Most plausible first: fewest coincidence-prone mistakes, then the earliest lines.
        fitting_combinations.sort(
            key=lambda candidate_combination: (
                sum(1 for candidate_mistake in candidate_combination if not candidate_mistake.is_plausible),
                [candidate_mistake.entry_mistake.ledger_entry.line_number for candidate_mistake in candidate_combination],
            )
        )
        return tuple(
            DiscrepancyExplanation(entry_mistakes=tuple(candidate_mistake.entry_mistake for candidate_mistake in candidate_combination))
            for candidate_combination in fitting_combinations
        )

    @staticmethod
    def _has_distinct_entries(candidate_combination: Iterable[CandidateMistake]) -> bool:
        line_numbers: list[int] = [candidate_mistake.entry_mistake.ledger_entry.line_number for candidate_mistake in candidate_combination]
        return len(set(line_numbers)) == len(line_numbers)

    @staticmethod
    def _summarize_cause(
        ledger_bucket: LedgerBucket, explained_ledger_bucket_composition: LedgerBucketComposition, composition_fit: CompositionFit | None
    ) -> str:
        bucket_label: str = AmountDiscrepancyDiagnosisProcessor._label_bucket(ledger_bucket)
        if composition_fit is None:
            return f"{bucket_label}: no combination of up to {MAXIMUM_MISTAKE_COUNT} entries explains the difference"
        policy_clause: str = AmountDiscrepancyDiagnosisProcessor._describe_policies(explained_ledger_bucket_composition.accepted_policy_names)
        if not composition_fit.discrepancy_explanations:
            return f"{bucket_label}: matches the reference{policy_clause}"
        first_discrepancy_explanation: DiscrepancyExplanation = composition_fit.discrepancy_explanations[0]
        mistakes_text: str = "; ".join(
            AmountDiscrepancyDiagnosisProcessor._describe_mistake(entry_mistake, ledger_bucket)
            for entry_mistake in first_discrepancy_explanation.entry_mistakes
        )
        other_explanation_count: int = len(composition_fit.discrepancy_explanations) - 1
        alternatives_clause: str = f" (or one of {other_explanation_count} other equally simple combinations)" if other_explanation_count else ""
        return f"{bucket_label}{policy_clause}: {mistakes_text}{alternatives_clause}"

    @staticmethod
    def _describe_cause(
        ledger_bucket: LedgerBucket,
        reported_amount: Decimal,
        explained_ledger_bucket_composition: LedgerBucketComposition,
        composition_fit: CompositionFit | None,
    ) -> str:
        bucket_label: str = AmountDiscrepancyDiagnosisProcessor._label_bucket(ledger_bucket)
        policy_clause: str = AmountDiscrepancyDiagnosisProcessor._describe_policies(explained_ledger_bucket_composition.accepted_policy_names)
        difference: Decimal = reported_amount - explained_ledger_bucket_composition.total_amount
        amounts_text: str = (
            f"{bucket_label}: reported {AmountDiscrepancyDiagnosisProcessor._format_amount(reported_amount)}, "
            f"reference {AmountDiscrepancyDiagnosisProcessor._format_amount(explained_ledger_bucket_composition.total_amount)}{policy_clause}"
        )
        if composition_fit is None:
            return (
                f"{amounts_text}, a difference of {AmountDiscrepancyDiagnosisProcessor._format_signed_amount(difference)} that no combination "
                f"of up to {MAXIMUM_MISTAKE_COUNT} entries explains (a broader categorization difference or an arithmetic error)."
            )
        if not composition_fit.discrepancy_explanations:
            return f"{amounts_text}: the reported amount matches the reference under an accepted policy."
        explanation_texts: list[str] = [
            " and ".join(
                AmountDiscrepancyDiagnosisProcessor._describe_mistake(entry_mistake, ledger_bucket, is_effect_shown=True)
                for entry_mistake in discrepancy_explanation.entry_mistakes
            )
            for discrepancy_explanation in composition_fit.discrepancy_explanations[:MAXIMUM_EXPLANATION_COUNT]
        ]
        unlisted_count: int = len(composition_fit.discrepancy_explanations) - len(explanation_texts)
        unlisted_clause: str = f"; {unlisted_count} more combinations also fit" if unlisted_count > 0 else ""
        lead_text: str = "Explained by:" if len(explanation_texts) == 1 else "Equally simple explanations: either"
        return (
            f"{amounts_text}, a difference of {AmountDiscrepancyDiagnosisProcessor._format_signed_amount(difference)}. "
            f"{lead_text} {'; or '.join(explanation_texts)}{unlisted_clause}."
        )

    @staticmethod
    def _describe_mistake(entry_mistake: EntryMistake, ledger_bucket: LedgerBucket, *, is_effect_shown: bool = False) -> str:
        ledger_entry: LedgerEntry = entry_mistake.ledger_entry
        entry_text: str = f'line {ledger_entry.line_number} "{" ".join(ledger_entry.source_text.split())}"'
        effect_clause: str = f" ({AmountDiscrepancyDiagnosisProcessor._format_signed_amount(entry_mistake.amount_effect)})" if is_effect_shown else ""
        match entry_mistake.entry_mistake_kind:
            case EntryMistakeKind.LEFT_OUT:
                return f"left out {entry_text}{effect_clause}"
            case EntryMistakeKind.SIGN_REVERSED:
                return f"counted {entry_text} with its sign reversed{effect_clause}"
            case EntryMistakeKind.WRONGLY_INCLUDED:
                reference_placement: str = AmountDiscrepancyDiagnosisProcessor._describe_reference_placement(ledger_entry, ledger_bucket)
                return f"counted {entry_text}{effect_clause}, which the reference {reference_placement}"

    @staticmethod
    def _describe_reference_placement(ledger_entry: LedgerEntry, ledger_bucket: LedgerBucket) -> str:
        if not ledger_entry.is_counted:
            return f"does not count ({ledger_entry.note})" if ledger_entry.note else "does not count"
        if not ledger_bucket.includes_period(ledger_entry.period):
            return f"puts in {ledger_entry.period}"
        return f"puts in {ledger_entry.category}"

    @staticmethod
    def _describe_policies(accepted_policy_names: tuple[str, ...]) -> str:
        if not accepted_policy_names:
            return ""
        return f" (under the accepted policy {', '.join(repr(accepted_policy_name) for accepted_policy_name in accepted_policy_names)})"

    @staticmethod
    def _label_bucket(ledger_bucket: LedgerBucket) -> str:
        return f"{ledger_bucket.category} {ledger_bucket.period}" if ledger_bucket.period is not None else f"{ledger_bucket.category}, all periods"

    @staticmethod
    def _format_amount(amount: Decimal) -> str:
        return f"{amount.quantize(CENT):,}"

    @staticmethod
    def _format_signed_amount(amount: Decimal) -> str:
        return f"{'+' if amount >= 0 else '-'}{abs(amount).quantize(CENT):,}"
