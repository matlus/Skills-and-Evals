import statistics
from collections.abc import Collection, Mapping, Sequence
from typing import final

from prompt_evals.managers.models.eval_suite_models import EvalSuite
from prompt_evals.managers.models.grading_models import TrialGrade
from prompt_evals.managers.models.scorecard_models import DurationSummary, ScorecardTiming, TrialTiming, VariantTiming
from prompt_evals.managers.models.trial_models import CompletedTrial, TrialIdentity, TrialRecord


@final
class ScorecardTimingProcessor:
    """Pairs each trial's answer time with its grading time and summarizes both, and their total, per graded variant.

    A trial whose session failed is left out of the summaries: it fails fast and would make a broken configuration look quick.
    """

    @staticmethod
    def summarize_timing(eval_suite: EvalSuite, trial_records: tuple[TrialRecord, ...], trial_grades: tuple[TrialGrade, ...]) -> ScorecardTiming:
        trial_timings: tuple[TrialTiming, ...] = ScorecardTimingProcessor._pair_trial_timings(trial_records, trial_grades)
        return ScorecardTiming(
            variant_timings=ScorecardTimingProcessor._summarize_variants(eval_suite, trial_timings),
            trial_timings=trial_timings,
        )

    @staticmethod
    def _pair_trial_timings(trial_records: Sequence[TrialRecord], trial_grades: Sequence[TrialGrade]) -> tuple[TrialTiming, ...]:
        grading_duration_seconds_by_trial_identity: Mapping[TrialIdentity, float] = {
            trial_grade.trial_identity: trial_grade.grading_duration_seconds for trial_grade in trial_grades
        }
        return tuple(
            ScorecardTimingProcessor._create_trial_timing(trial_record, grading_duration_seconds_by_trial_identity[trial_record.trial_identity])
            for trial_record in trial_records
        )

    @staticmethod
    def _create_trial_timing(trial_record: TrialRecord, grading_duration_seconds: float) -> TrialTiming:
        answer_duration_seconds: float | None = trial_record.answer_duration_seconds
        return TrialTiming(
            trial_identity=trial_record.trial_identity,
            session_answered=isinstance(trial_record, CompletedTrial),
            answer_duration_seconds=answer_duration_seconds,
            grading_duration_seconds=grading_duration_seconds,
            total_duration_seconds=None if answer_duration_seconds is None else answer_duration_seconds + grading_duration_seconds,
        )

    @staticmethod
    def _summarize_variants(eval_suite: EvalSuite, trial_timings: Sequence[TrialTiming]) -> tuple[VariantTiming, ...]:
        graded_variant_names: set[str] = {trial_timing.trial_identity.variant_name for trial_timing in trial_timings}
        return tuple(
            ScorecardTimingProcessor._summarize_variant(prompt_variant.variant_name, eval_suite.gated_variant_names, trial_timings)
            for prompt_variant in eval_suite.prompt_variants
            if prompt_variant.variant_name in graded_variant_names
        )

    @staticmethod
    def _summarize_variant(variant_name: str, gated_variant_names: Collection[str], trial_timings: Sequence[TrialTiming]) -> VariantTiming:
        variant_trial_timings: list[TrialTiming] = [
            trial_timing for trial_timing in trial_timings if trial_timing.trial_identity.variant_name == variant_name
        ]
        answered_trial_timings: list[TrialTiming] = [trial_timing for trial_timing in variant_trial_timings if trial_timing.session_answered]
        return VariantTiming(
            variant_name=variant_name,
            is_gated=variant_name in gated_variant_names,
            trial_count=len(variant_trial_timings),
            answer_duration_summary=ScorecardTimingProcessor._summarize_durations(
                [trial_timing.answer_duration_seconds for trial_timing in answered_trial_timings]
            ),
            grading_duration_summary=ScorecardTimingProcessor._summarize_durations(
                [trial_timing.grading_duration_seconds for trial_timing in answered_trial_timings]
            ),
            total_duration_summary=ScorecardTimingProcessor._summarize_durations(
                [trial_timing.total_duration_seconds for trial_timing in answered_trial_timings]
            ),
        )

    @staticmethod
    def _summarize_durations(durations_seconds: Sequence[float | None]) -> DurationSummary | None:
        # A trial without a time is left out rather than counted as zero, so the summary says how many trials it covers.
        measured_durations_seconds: list[float] = [duration_seconds for duration_seconds in durations_seconds if duration_seconds is not None]
        if not measured_durations_seconds:
            return None
        return DurationSummary(
            median_seconds=statistics.median(measured_durations_seconds),
            minimum_seconds=min(measured_durations_seconds),
            maximum_seconds=max(measured_durations_seconds),
            measured_trial_count=len(measured_durations_seconds),
        )
