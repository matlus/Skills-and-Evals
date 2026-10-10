from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from prompt_evals.managers.models.diagnosis_models import AmountDiscrepancyDiagnosis, DisputedAmount
from prompt_evals.managers.models.trial_models import TrialIdentity


class CheckStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    ERRORED = "errored"


@dataclass(frozen=True)
class CheckOutcome:
    """`amount_discrepancy_diagnoses` explain a failed check's wrong totals from the case's reference ledger; empty when
    the check passed, the case has no ledger, or no wrong total could be matched to a ledger bucket."""

    check_name: str
    trial_identity: TrialIdentity
    check_status: CheckStatus
    reason: str
    amount_discrepancy_diagnoses: tuple[AmountDiscrepancyDiagnosis, ...]


@dataclass(frozen=True)
class ExtractedFact:
    fact_name: str
    reported_value: str | None


@dataclass(frozen=True)
class ExtractedFacts:
    extracted_facts: tuple[ExtractedFact, ...]

    def read_reported_value(self, fact_name: str) -> str | None:
        """None when the extractor reported null because the answer never states the fact. Fact names are unique,
        because the extractor reports them as the keys of one JSON object."""
        reported_values: list[str | None] = [
            extracted_fact.reported_value for extracted_fact in self.extracted_facts if extracted_fact.fact_name == fact_name
        ]
        return reported_values[0] if reported_values else None


@dataclass(frozen=True)
class JudgeVerdict:
    is_passed: bool
    reason: str
    disputed_amounts: tuple[DisputedAmount, ...]


@dataclass(frozen=True)
class TrialGrade:
    trial_identity: TrialIdentity
    extracted_facts: ExtractedFacts | None
    check_outcomes: tuple[CheckOutcome, ...]


@dataclass(frozen=True)
class SucceededFactExtraction:
    extracted_facts: ExtractedFacts


@dataclass(frozen=True)
class FailedFactExtraction:
    failure_description: str


type FactExtractionAttempt = SucceededFactExtraction | FailedFactExtraction


@dataclass(frozen=True)
class SucceededJudgment:
    judge_verdict: JudgeVerdict


@dataclass(frozen=True)
class FailedJudgment:
    failure_description: str


type JudgmentAttempt = SucceededJudgment | FailedJudgment


@dataclass(frozen=True)
class GraderReports:
    """What the graders reported about one completed trial's answer: the facts it states and each judge check's verdict."""

    fact_extraction_attempt: FactExtractionAttempt
    judgment_attempt_by_check_name: Mapping[str, JudgmentAttempt]
