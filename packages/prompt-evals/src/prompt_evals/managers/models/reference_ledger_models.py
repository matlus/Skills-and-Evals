from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class LedgerEntry:
    """One line of a case's input data as the reference key reads it.

    `alternative_categories` are other categories the key also accepts for this entry. They belong to the accepted
    policy `policy_name` (for example "Barnes & Noble in Shopping"); every entry of one policy switches together.
    An entry that is not counted (for example a likely duplicate) is in the ledger but in no reference total.
    """

    line_number: int
    source_text: str
    period: str
    amount: Decimal
    category: str
    alternative_categories: tuple[str, ...]
    policy_name: str | None
    is_counted: bool
    note: str | None


@dataclass(frozen=True)
class LedgerBucket:
    """The entries of one category in one period, or in every period when `period` is None."""

    category: str
    period: str | None

    def includes_period(self, period: str) -> bool:
        return self.period is None or self.period == period


@dataclass(frozen=True)
class AmountFactLedgerBucket:
    """An amount fact whose reference value is the total of a ledger bucket."""

    fact_name: str
    ledger_bucket: LedgerBucket


@dataclass(frozen=True)
class LedgerBucketComposition:
    """The entries that make up a bucket's reference total once the named accepted policies are applied.
    With no policy applied, it is the reference key's own total."""

    ledger_bucket: LedgerBucket
    accepted_policy_names: tuple[str, ...]
    member_entries: tuple[LedgerEntry, ...]
    total_amount: Decimal


@dataclass(frozen=True)
class LedgerBucketTotals:
    """A bucket's reference composition first, then one per combination of the accepted policies that change the bucket,
    fewest policies first."""

    ledger_bucket: LedgerBucket
    ledger_bucket_compositions: tuple[LedgerBucketComposition, ...]


@dataclass(frozen=True)
class ReferenceLedger:
    """The reference key at entry level, so a wrong total can be traced to the entries that make the difference.

    `ledger_bucket_totals` total every category in every period, then every category across all periods, then any other
    bucket an amount fact names. `ledger_bucket_totals_by_fact_name` are the totals of the bucket each amount fact names.
    """

    ledger_entries: tuple[LedgerEntry, ...]
    ledger_bucket_totals: tuple[LedgerBucketTotals, ...]
    ledger_bucket_totals_by_fact_name: Mapping[str, LedgerBucketTotals]
