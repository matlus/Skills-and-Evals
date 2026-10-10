from dataclasses import dataclass

from prompt_evals.managers.models.evaluation_models import CodingAssistant, EffortLevel


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
    passes_gate: bool
