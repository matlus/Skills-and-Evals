from collections.abc import Iterable
from decimal import Decimal
from itertools import combinations
from typing import final

from prompt_evals.managers.models.reference_ledger_models import (
    AmountFactLedgerBucket,
    LedgerBucket,
    LedgerBucketComposition,
    LedgerBucketTotals,
    LedgerEntry,
    ReferenceLedger,
)


@final
class ReferenceLedgerTotalsProcessor:
    """Totals of ledger buckets under the reference key's own policy and under every combination of its accepted policies."""

    @staticmethod
    def total_reference_ledger(
        ledger_entries: tuple[LedgerEntry, ...], amount_fact_ledger_buckets: tuple[AmountFactLedgerBucket, ...]
    ) -> ReferenceLedger:
        ledger_bucket_totals_by_ledger_bucket: dict[LedgerBucket, LedgerBucketTotals] = {
            ledger_bucket: ReferenceLedgerTotalsProcessor._total_ledger_bucket(ledger_entries, ledger_bucket)
            for ledger_bucket in ReferenceLedgerTotalsProcessor._list_ledger_buckets(ledger_entries, amount_fact_ledger_buckets)
        }
        return ReferenceLedger(
            ledger_entries=ledger_entries,
            ledger_bucket_totals=tuple(ledger_bucket_totals_by_ledger_bucket.values()),
            ledger_bucket_totals_by_fact_name={
                amount_fact_ledger_bucket.fact_name: ledger_bucket_totals_by_ledger_bucket[amount_fact_ledger_bucket.ledger_bucket]
                for amount_fact_ledger_bucket in amount_fact_ledger_buckets
            },
        )

    @staticmethod
    def _list_ledger_buckets(
        ledger_entries: tuple[LedgerEntry, ...], amount_fact_ledger_buckets: tuple[AmountFactLedgerBucket, ...]
    ) -> tuple[LedgerBucket, ...]:
        """Every category in every period, then every category across all periods, then any other bucket an amount fact names."""
        categories: list[str] = list(dict.fromkeys(ledger_entry.category for ledger_entry in ledger_entries))
        periods: list[str] = sorted({ledger_entry.period for ledger_entry in ledger_entries})
        return tuple(
            dict.fromkeys(
                (
                    *(LedgerBucket(category=category, period=period) for category in categories for period in periods),
                    *(LedgerBucket(category=category, period=None) for category in categories),
                    *(amount_fact_ledger_bucket.ledger_bucket for amount_fact_ledger_bucket in amount_fact_ledger_buckets),
                )
            )
        )

    @staticmethod
    def _total_ledger_bucket(ledger_entries: tuple[LedgerEntry, ...], ledger_bucket: LedgerBucket) -> LedgerBucketTotals:
        entries_in_scope: tuple[LedgerEntry, ...] = ReferenceLedgerTotalsProcessor._select_entries_in_scope(ledger_entries, ledger_bucket)
        policy_combinations: tuple[tuple[str, ...], ...] = ReferenceLedgerTotalsProcessor._list_policy_combinations(
            ReferenceLedgerTotalsProcessor._find_relevant_policy_names(entries_in_scope, ledger_bucket)
        )
        return LedgerBucketTotals(
            ledger_bucket=ledger_bucket,
            ledger_bucket_compositions=tuple(
                ReferenceLedgerTotalsProcessor._compose_under_policies(entries_in_scope, ledger_bucket, accepted_policy_names)
                for accepted_policy_names in policy_combinations
            ),
        )

    @staticmethod
    def _select_entries_in_scope(ledger_entries: tuple[LedgerEntry, ...], ledger_bucket: LedgerBucket) -> tuple[LedgerEntry, ...]:
        return tuple(
            ledger_entry for ledger_entry in ledger_entries if ledger_entry.is_counted and ledger_bucket.includes_period(ledger_entry.period)
        )

    @staticmethod
    def _find_relevant_policy_names(entries_in_scope: Iterable[LedgerEntry], ledger_bucket: LedgerBucket) -> tuple[str, ...]:
        # A policy matters to a bucket when it can move an entry into it or out of it.
        return tuple(
            dict.fromkeys(
                ledger_entry.policy_name
                for ledger_entry in entries_in_scope
                if ledger_entry.policy_name is not None and ledger_bucket.category in (ledger_entry.category, *ledger_entry.alternative_categories)
            )
        )

    @staticmethod
    def _list_policy_combinations(relevant_policy_names: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
        """No policy first, then every combination of the relevant policies, fewest policies first."""
        return tuple(
            accepted_policy_names
            for policy_count in range(len(relevant_policy_names) + 1)
            for accepted_policy_names in combinations(relevant_policy_names, policy_count)
        )

    @staticmethod
    def _compose_under_policies(
        entries_in_scope: Iterable[LedgerEntry], ledger_bucket: LedgerBucket, accepted_policy_names: tuple[str, ...]
    ) -> LedgerBucketComposition:
        # Under an accepted policy an entry may sit in any of its alternative categories; otherwise it stays in its reference category.
        member_entries: tuple[LedgerEntry, ...] = tuple(
            ledger_entry
            for ledger_entry in entries_in_scope
            if ledger_bucket.category
            in (ledger_entry.alternative_categories if ledger_entry.policy_name in accepted_policy_names else (ledger_entry.category,))
        )
        return LedgerBucketComposition(
            ledger_bucket=ledger_bucket,
            accepted_policy_names=accepted_policy_names,
            member_entries=member_entries,
            total_amount=sum((ledger_entry.amount for ledger_entry in member_entries), Decimal(0)),
        )
