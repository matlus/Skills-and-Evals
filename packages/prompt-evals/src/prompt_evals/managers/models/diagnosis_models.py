from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from prompt_evals.managers.models.reference_ledger_models import LedgerBucket, LedgerEntry


class EntryMistakeKind(StrEnum):
    LEFT_OUT = "left_out"
    WRONGLY_INCLUDED = "wrongly_included"
    SIGN_REVERSED = "sign_reversed"


@dataclass(frozen=True)
class EntryMistake:
    """One entry handled differently from the reference; `amount_effect` is how much it moved the reported total."""

    ledger_entry: LedgerEntry
    entry_mistake_kind: EntryMistakeKind
    amount_effect: Decimal


@dataclass(frozen=True)
class DiscrepancyExplanation:
    """A set of entry mistakes whose effects add up exactly to the difference between the reported and reference totals."""

    entry_mistakes: tuple[EntryMistake, ...]


@dataclass(frozen=True)
class AmountDiscrepancyDiagnosis:
    """Why a reported total differs from the reference ledger.

    `reference_amount` is the bucket's total under `accepted_policy_names`, the accepted policies closest to the answer.
    `discrepancy_explanations` lists every simplest explanation found, most plausible first; it is empty when no
    combination of a few entries accounts for the difference. `cause_summary` names the cause without the amounts,
    so the same mistake in several runs reads the same; `cause_description` adds the amounts.
    """

    ledger_bucket: LedgerBucket
    reported_amount: Decimal
    reference_amount: Decimal
    accepted_policy_names: tuple[str, ...]
    discrepancy_explanations: tuple[DiscrepancyExplanation, ...]
    cause_summary: str
    cause_description: str


@dataclass(frozen=True)
class DisputedAmount:
    """A number a judge rejected because it contradicts a reference value, as the judge quoted both."""

    description: str
    answer_amount_text: str
    reference_amount_text: str
