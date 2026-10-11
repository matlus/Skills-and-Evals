from collections.abc import Sequence
from typing import Final, final

from prompt_evals_app.scorecard_document_resources import DurationRangeResource
from prompt_evals_app.scorecard_summary_reader import VariantResult

GATE_MET_MARK: Final[str] = "✅"
GATE_MISSED_MARK: Final[str] = "❌"
SECONDS_PER_MINUTE: Final[int] = 60
SECONDS_PER_HOUR: Final[int] = 3600
# Below this many seconds a time is shown to a tenth of a second; above it, a tenth is noise.
TENTHS_SHOWN_BELOW_SECONDS: Final[float] = 10.0
NOT_RECORDED_TEXT: Final[str] = "not recorded"
RANGE_SEPARATOR: Final[str] = " to "


@final
class ScorecardComparisonRenderer:
    """Renders the newest result of every configuration as one Markdown table: one row per assistant, model, effort and
    prompt variant, with the gate, the checks below their minimum, and the three per-run times."""

    @staticmethod
    def render_comparison(eval_suite_name: str, variant_results: Sequence[VariantResult]) -> str:
        report_lines: list[str] = [
            f"# Scorecard comparison: {eval_suite_name}",
            "",
            (
                "Generated from each run folder's scorecard.json; for every assistant, model, effort and prompt variant only the newest "
                "run is shown. Answer time is the coding-assistant session that produced the answer, before any grading started. "
                "Grading time is the eval analysis of that answer: reading its facts, every judge, and the code checks. Total time is "
                "the two added together. Each time is the median per run, then the shortest to the longest run. Runs whose session "
                "failed are left out of these times, and so are runs recorded before answer times were saved; a cell then says how "
                "many runs it covers."
            ),
            "",
            (
                "| Assistant | Model | Effort | Variant | Runs | Gate | Checks below minimum | Errored checks | Answer time (model session) | "
                "Grading time (eval analysis) | Total time | Run folder |"
            ),
            "|---|---|---|---|---|---|---|---|---|---|---|---|",
            *(ScorecardComparisonRenderer._render_line(variant_result) for variant_result in variant_results),
        ]
        if not variant_results:
            report_lines.append("No run folder holds a scorecard.json.")
        return "\n".join(report_lines) + "\n"

    @staticmethod
    def _render_line(variant_result: VariantResult) -> str:
        table_cells: list[str] = [
            variant_result.coding_assistant,
            variant_result.model_name,
            variant_result.effort_level,
            variant_result.variant_name,
            str(variant_result.trial_count),
            ScorecardComparisonRenderer._render_gate(variant_result),
            ", ".join(variant_result.checks_below_minimum) or "none",
            str(variant_result.errored_check_count),
            *(
                ScorecardComparisonRenderer._render_duration_range(duration_range, variant_result.trial_count)
                for duration_range in (
                    variant_result.answer_duration_range,
                    variant_result.grading_duration_range,
                    variant_result.total_duration_range,
                )
            ),
            f"`{variant_result.run_folder_name}`",
        ]
        return "| " + " | ".join(ScorecardComparisonRenderer._escape_table_cell(table_cell) for table_cell in table_cells) + " |"

    @staticmethod
    def _escape_table_cell(cell_text: str) -> str:
        # A name written in an eval suite can hold a newline, which would end the table row; scorecard.json keeps the full text.
        return " ".join(cell_text.split()).replace("|", "\\|")

    @staticmethod
    def _render_gate(variant_result: VariantResult) -> str:
        if not variant_result.is_gated:
            return "measured only"
        return f"{GATE_MET_MARK} passed" if variant_result.passes_gate else f"{GATE_MISSED_MARK} failed"

    @staticmethod
    def _render_duration_range(duration_range: DurationRangeResource | None, trial_count: int) -> str:
        if duration_range is None:
            return NOT_RECORDED_TEXT
        range_text: str = (
            f"{ScorecardComparisonRenderer._format_duration(duration_range.median_seconds)} "
            f"({ScorecardComparisonRenderer._format_duration(duration_range.minimum_seconds)}{RANGE_SEPARATOR}"
            f"{ScorecardComparisonRenderer._format_duration(duration_range.maximum_seconds)})"
        )
        if duration_range.measured_trial_count < trial_count:
            range_text += f", {duration_range.measured_trial_count} of {trial_count} runs"
        return range_text

    @staticmethod
    def _format_duration(duration_seconds: float) -> str:
        if duration_seconds < TENTHS_SHOWN_BELOW_SECONDS:
            return f"{duration_seconds:.1f}s"
        whole_seconds: int = round(duration_seconds)
        if whole_seconds < SECONDS_PER_MINUTE:
            return f"{whole_seconds}s"
        if whole_seconds < SECONDS_PER_HOUR:
            return f"{whole_seconds // SECONDS_PER_MINUTE}m {whole_seconds % SECONDS_PER_MINUTE:02d}s"
        return f"{whole_seconds // SECONDS_PER_HOUR}h {whole_seconds % SECONDS_PER_HOUR // SECONDS_PER_MINUTE:02d}m"
