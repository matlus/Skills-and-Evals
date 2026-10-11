from dataclasses import dataclass


@dataclass(frozen=True)
class ScorecardRowResource:
    """One check of one prompt variant, as a scorecard.json row records it."""

    check_name: str
    variant_name: str
    trial_count: int
    passed_count: int
    errored_count: int
    is_gated: bool
    meets_minimum_pass_rate: bool


@dataclass(frozen=True)
class DurationRangeResource:
    median_seconds: float
    minimum_seconds: float
    maximum_seconds: float
    measured_trial_count: int


@dataclass(frozen=True)
class VariantTimingResource:
    """One prompt variant's per-run times. A range is None when that run recorded no such time."""

    variant_name: str
    answer_duration_range: DurationRangeResource | None
    grading_duration_range: DurationRangeResource | None
    total_duration_range: DurationRangeResource | None


@dataclass(frozen=True)
class ScorecardDocumentResource:
    """The part of a scorecard.json the comparison reads. `variant_timings` is empty for a scorecard written before
    timing was recorded."""

    coding_assistant: str
    model_name: str
    effort_level: str
    passes_gate: bool
    scorecard_rows: tuple[ScorecardRowResource, ...]
    variant_timings: tuple[VariantTimingResource, ...]
