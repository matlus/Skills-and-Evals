from dataclasses import dataclass

from prompt_evals.managers.models.evaluation_models import CodingAssistant, EffortLevel
from prompt_evals.managers.models.trial_models import TrialIdentity


@dataclass(frozen=True)
class ScorecardRow:
    check_name: str
    description: str
    variant_name: str
    trial_count: int
    passed_count: int
    errored_count: int
    pass_rate: float
    minimum_pass_rate: float
    is_gated: bool
    meets_minimum_pass_rate: bool
    failure_reasons: tuple[str, ...]


@dataclass(frozen=True)
class FailureCause:
    """One traced cause of failed checks and every place it occurred, as "<variant> / <case> / run-NN / <check>"."""

    cause_summary: str
    occurrence_labels: tuple[str, ...]


@dataclass(frozen=True)
class TrialTiming:
    """One trial's times in seconds. Answer time is the session that produced the answer, before grading started; grading
    time is everything that graded it. The answer and total times are None when a recorded trial's run saved no answer time.
    `session_answered` is False for a trial whose session failed; it is graded at once and its times are not summarized."""

    trial_identity: TrialIdentity
    session_answered: bool
    answer_duration_seconds: float | None
    grading_duration_seconds: float
    total_duration_seconds: float | None


@dataclass(frozen=True)
class DurationSummary:
    """One kind of time across the trials that have it: the median, the shortest and the longest, in seconds."""

    median_seconds: float
    minimum_seconds: float
    maximum_seconds: float
    measured_trial_count: int


@dataclass(frozen=True)
class VariantTiming:
    """The per-run times of one prompt variant, over the trials whose session answered. A summary is None when none of
    them has that time."""

    variant_name: str
    is_gated: bool
    trial_count: int
    answer_duration_summary: DurationSummary | None
    grading_duration_summary: DurationSummary | None
    total_duration_summary: DurationSummary | None


@dataclass(frozen=True)
class ScorecardTiming:
    """How long the trials took: every trial's times, and their summary per graded variant in the order of the scorecard rows."""

    variant_timings: tuple[VariantTiming, ...]
    trial_timings: tuple[TrialTiming, ...]


@dataclass(frozen=True)
class Scorecard:
    """Pass rates per check per prompt variant. Only gated variants decide `passes_gate`;
    the others are measured for comparison (for example, a baseline prompt).

    `failure_causes` groups the failed checks whose wrong totals were traced in a reference ledger, most frequent first.
    """

    eval_suite_name: str
    coding_assistant: CodingAssistant
    model_name: str
    effort_level: EffortLevel
    repetitions: int
    scorecard_rows: tuple[ScorecardRow, ...]
    failure_causes: tuple[FailureCause, ...]
    scorecard_timing: ScorecardTiming
    passes_gate: bool
