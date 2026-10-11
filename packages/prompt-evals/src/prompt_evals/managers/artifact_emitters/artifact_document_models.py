from dataclasses import dataclass

from prompt_evals.managers.models.trial_models import TrialIdentity


@dataclass(frozen=True)
class EntryMistakeDocument:
    line_number: int
    source_text: str
    mistake: str
    amount_effect: str
    reference_category: str
    reference_period: str


@dataclass(frozen=True)
class AmountDiagnosisDocument:
    """Why one reported total is wrong. `explanations` lists each simplest set of entry mistakes that accounts for the
    difference, most plausible first; it is empty when none was found."""

    category: str
    period: str | None
    reported_amount: str
    reference_amount: str
    accepted_policies: tuple[str, ...]
    cause: str
    explanations: tuple[tuple[EntryMistakeDocument, ...], ...]


@dataclass(frozen=True)
class CheckOutcomeDocument:
    check_name: str
    check_status: str
    reason: str
    diagnoses: tuple[AmountDiagnosisDocument, ...]


@dataclass(frozen=True)
class TrialGradeDocument:
    """The grade.json document: the trial's identity, what the extractor read from the answer, every check outcome, and
    how long grading took."""

    trial_identity: TrialIdentity
    extracted_facts: dict[str, str | None] | None
    check_outcomes: tuple[CheckOutcomeDocument, ...]
    grading_duration_seconds: float


@dataclass(frozen=True)
class TrialTimingDocument:
    """The timing.json document: how long the session took to produce the answer, so a regrade can report it again.
    None when the trial was regraded from a run that saved no answer time."""

    answer_duration_seconds: float | None
