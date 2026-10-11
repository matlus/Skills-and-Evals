from collections.abc import Iterable, Iterator, Sequence
from decimal import ROUND_FLOOR, Decimal
from itertools import groupby
from typing import Final, final

from prompt_evals.managers.models.scorecard_models import DurationSummary, FailureCause, Scorecard, ScorecardRow, VariantTiming

GATE_MET_MARK: Final[str] = "✅"
GATE_MISSED_MARK: Final[str] = "❌"
PERCENTAGE_PER_RATE: Final[Decimal] = Decimal(100)
SECONDS_PER_MINUTE: Final[int] = 60
SECONDS_PER_HOUR: Final[int] = 3600
# Below this many seconds a time is shown to a tenth of a second; above it, a tenth is noise.
TENTHS_SHOWN_BELOW_SECONDS: Final[float] = 10.0
NOT_RECORDED_TEXT: Final[str] = "not recorded"
RANGE_SEPARATOR: Final[str] = " to "
GATED_VARIANT_LABEL: Final[str] = " (gated)"


@final
class ScorecardReportRenderingProcessor:
    """Renders the scorecard as a Markdown table: checks down the side, prompt variants across the top.

    Aggregation emits rows check by check, with the variants in the same order inside every check,
    so consecutive rows with one check name form one table line.
    """

    @staticmethod
    def render_scorecard_report(scorecard: Scorecard) -> str:
        rows_per_check: list[list[ScorecardRow]] = ScorecardReportRenderingProcessor._group_rows_per_check(scorecard)
        report_lines: list[str] = [
            *ScorecardReportRenderingProcessor._render_heading(scorecard),
            *ScorecardReportRenderingProcessor._render_table(rows_per_check),
            *ScorecardReportRenderingProcessor._render_timing(scorecard.scorecard_timing.variant_timings),
            *ScorecardReportRenderingProcessor._render_descriptions(rows_per_check),
            *ScorecardReportRenderingProcessor._render_failure_causes(scorecard.failure_causes),
            *ScorecardReportRenderingProcessor._render_failures(scorecard),
        ]
        return "\n".join(report_lines) + "\n"

    @staticmethod
    def _group_rows_per_check(scorecard: Scorecard) -> list[list[ScorecardRow]]:
        rows_per_check: list[list[ScorecardRow]] = []
        _check_name: str
        check_rows: Iterator[ScorecardRow]
        for _check_name, check_rows in groupby(scorecard.scorecard_rows, key=lambda scorecard_row: scorecard_row.check_name):
            rows_per_check.append(list(check_rows))
        return rows_per_check

    @staticmethod
    def _render_heading(scorecard: Scorecard) -> list[str]:
        has_gated_rows: bool = any(scorecard_row.is_gated for scorecard_row in scorecard.scorecard_rows)
        gate_result: str = ("PASSED" if scorecard.passes_gate else "FAILED") if has_gated_rows else "NOT EVALUATED (no gated variant was run)"
        repetitions_label: str = f"Repetitions per case: {scorecard.repetitions}"
        return [
            f"# Scorecard: {ScorecardReportRenderingProcessor._flatten_to_one_line(scorecard.eval_suite_name)}",
            "",
            (
                f"Assistant: `{scorecard.coding_assistant}` · Model: `{scorecard.model_name}` · Effort: `{scorecard.effort_level}` · "
                f"{repetitions_label} · Gate: **{gate_result}**"
            ),
            "",
            "Gated variants must reach each check's minimum pass rate. Other variants are measured for comparison only.",
            "",
        ]

    @staticmethod
    def _render_table(rows_per_check: Sequence[Sequence[ScorecardRow]]) -> list[str]:
        if not rows_per_check:
            return ["No checks were graded."]
        variant_headings: list[str] = [
            ScorecardReportRenderingProcessor._escape_table_cell(
                f"{scorecard_row.variant_name}{GATED_VARIANT_LABEL}" if scorecard_row.is_gated else scorecard_row.variant_name
            )
            for scorecard_row in rows_per_check[0]
        ]
        table_lines: list[str] = [
            "| Check | Minimum | " + " | ".join(variant_headings) + " |",
            "|---|---|" + "---|" * len(variant_headings),
        ]
        table_lines.extend(ScorecardReportRenderingProcessor._render_table_line(check_rows) for check_rows in rows_per_check)
        return table_lines

    @staticmethod
    def _render_table_line(check_rows: Sequence[ScorecardRow]) -> str:
        table_cells: list[str] = [
            ScorecardReportRenderingProcessor._escape_table_cell(check_rows[0].check_name),
            ScorecardReportRenderingProcessor._render_minimum_pass_rate(check_rows[0].minimum_pass_rate),
            *(ScorecardReportRenderingProcessor._render_cell(check_row) for check_row in check_rows),
        ]
        return "| " + " | ".join(table_cells) + " |"

    @staticmethod
    def _render_timing(variant_timings: Sequence[VariantTiming]) -> list[str]:
        if not variant_timings:
            return []
        return [
            "",
            "## Time per run",
            "",
            (
                "Answer time is the coding-assistant session that produced the answer, before any grading started. Grading time is "
                "the eval analysis of that answer: reading its facts, every judge, and the code checks. Total time is the two added "
                "together. Each cell is the median across runs, then the shortest to the longest run. Runs execute concurrently, "
                "so the whole evaluation takes less time than the runs added together. Runs whose session failed are left out of these "
                "times, and so are runs recorded before answer times were saved; a cell then says how many runs it covers."
            ),
            "",
            "| Variant | Runs | Answer time (model session) | Grading time (eval analysis) | Total time |",
            "|---|---|---|---|---|",
            *(ScorecardReportRenderingProcessor._render_timing_line(variant_timing) for variant_timing in variant_timings),
        ]

    @staticmethod
    def _render_timing_line(variant_timing: VariantTiming) -> str:
        variant_heading: str = f"{variant_timing.variant_name}{GATED_VARIANT_LABEL}" if variant_timing.is_gated else variant_timing.variant_name
        table_cells: list[str] = [
            ScorecardReportRenderingProcessor._escape_table_cell(variant_heading),
            str(variant_timing.trial_count),
            *(
                ScorecardReportRenderingProcessor._render_duration_summary(duration_summary, variant_timing.trial_count)
                for duration_summary in (
                    variant_timing.answer_duration_summary,
                    variant_timing.grading_duration_summary,
                    variant_timing.total_duration_summary,
                )
            ),
        ]
        return "| " + " | ".join(table_cells) + " |"

    @staticmethod
    def _render_duration_summary(duration_summary: DurationSummary | None, trial_count: int) -> str:
        if duration_summary is None:
            return NOT_RECORDED_TEXT
        summary_text: str = (
            f"{ScorecardReportRenderingProcessor._format_duration(duration_summary.median_seconds)} "
            f"({ScorecardReportRenderingProcessor._format_duration(duration_summary.minimum_seconds)}{RANGE_SEPARATOR}"
            f"{ScorecardReportRenderingProcessor._format_duration(duration_summary.maximum_seconds)})"
        )
        if duration_summary.measured_trial_count < trial_count:
            summary_text += f", {duration_summary.measured_trial_count} of {trial_count} runs"
        return summary_text

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

    @staticmethod
    def _render_descriptions(rows_per_check: Iterable[Sequence[ScorecardRow]]) -> list[str]:
        return [
            "",
            "## Check descriptions",
            "",
            *(ScorecardReportRenderingProcessor._render_description(check_rows[0]) for check_rows in rows_per_check),
        ]

    @staticmethod
    def _render_description(scorecard_row: ScorecardRow) -> str:
        check_name: str = ScorecardReportRenderingProcessor._flatten_to_one_line(scorecard_row.check_name)
        description: str = ScorecardReportRenderingProcessor._flatten_to_one_line(scorecard_row.description)
        return f"- **{check_name}**: {description}"

    @staticmethod
    def _escape_table_cell(cell_text: str) -> str:
        return ScorecardReportRenderingProcessor._flatten_to_one_line(cell_text).replace("|", "\\|")

    @staticmethod
    def _render_cell(scorecard_row: ScorecardRow) -> str:
        pass_rate_text: str = ScorecardReportRenderingProcessor._render_pass_rate(scorecard_row.pass_rate, scorecard_row.minimum_pass_rate)
        cell_text: str = f"{scorecard_row.passed_count}/{scorecard_row.trial_count} ({pass_rate_text})"
        if scorecard_row.errored_count:
            cell_text += f", {scorecard_row.errored_count} errored"
        if not scorecard_row.is_gated:
            return cell_text
        return f"{GATE_MET_MARK if scorecard_row.meets_minimum_pass_rate else GATE_MISSED_MARK} {cell_text}"

    @staticmethod
    def _render_minimum_pass_rate(minimum_pass_rate: float) -> str:
        return f"{ScorecardReportRenderingProcessor._to_minimum_percentage(minimum_pass_rate):f}%"

    @staticmethod
    def _render_pass_rate(pass_rate: float, minimum_pass_rate: float) -> str:
        # Truncated, never rounded, to the precision the minimum is shown with, so the shown rate cannot contradict the gate
        # mark: a rate that missed the minimum always reads lower than it, and a rate that met it never does.
        decimal_places: int = ScorecardReportRenderingProcessor._count_decimal_places(
            ScorecardReportRenderingProcessor._to_minimum_percentage(minimum_pass_rate)
        )
        truncated_percentage: Decimal = ScorecardReportRenderingProcessor._to_percentage(pass_rate).quantize(
            Decimal(1).scaleb(-decimal_places), rounding=ROUND_FLOOR
        )
        return f"{truncated_percentage:f}%"

    @staticmethod
    def _to_minimum_percentage(minimum_pass_rate: float) -> Decimal:
        # Normalized, so the minimum shows exactly the digits its author wrote: 0.67 as 67, 0.675 as 67.5.
        return ScorecardReportRenderingProcessor._to_percentage(minimum_pass_rate).normalize()

    @staticmethod
    def _to_percentage(rate: float) -> Decimal:
        # str() gives the shortest decimal that reads back as the same float and keeps the order of floats, so these exact
        # percentages compare the way the aggregation compared the rates when it decided the gate mark.
        return Decimal(str(rate)) * PERCENTAGE_PER_RATE

    @staticmethod
    def _count_decimal_places(percentage: Decimal) -> int:
        exponent: int | str = percentage.as_tuple().exponent
        return -exponent if isinstance(exponent, int) and exponent < 0 else 0

    @staticmethod
    def _render_failure_causes(failure_causes: Sequence[FailureCause]) -> list[str]:
        if not failure_causes:
            return []
        return [
            "",
            "## Failure causes",
            "",
            (
                "Wrong totals traced entry by entry in the case's reference ledger. One cause in several runs is a systematic mistake, "
                "or a reference key that is stricter than it should be."
            ),
            "",
            *(
                (
                    f"- **{ScorecardReportRenderingProcessor._flatten_to_one_line(failure_cause.cause_summary)}** · "
                    f"{len(failure_cause.occurrence_labels)} {'check' if len(failure_cause.occurrence_labels) == 1 else 'checks'}: "
                )
                + "; ".join(
                    ScorecardReportRenderingProcessor._flatten_to_one_line(occurrence_label) for occurrence_label in failure_cause.occurrence_labels
                )
                for failure_cause in failure_causes
            ),
        ]

    @staticmethod
    def _render_failures(scorecard: Scorecard) -> list[str]:
        failure_lines: list[str] = ["", "## Runs that did not pass", ""]
        rows_with_failures: list[ScorecardRow] = [scorecard_row for scorecard_row in scorecard.scorecard_rows if scorecard_row.failure_reasons]
        if not rows_with_failures:
            failure_lines.append("Every run passed every check.")
            return failure_lines
        for scorecard_row in rows_with_failures:
            failure_heading: str = f"{scorecard_row.check_name} · {scorecard_row.variant_name}"
            failure_lines.extend((f"### {ScorecardReportRenderingProcessor._flatten_to_one_line(failure_heading)}", ""))
            failure_lines.extend(
                f"- {ScorecardReportRenderingProcessor._flatten_to_one_line(failure_reason)}" for failure_reason in scorecard_row.failure_reasons
            )
            failure_lines.append("")
        return failure_lines

    @staticmethod
    def _flatten_to_one_line(report_text: str) -> str:
        # Reasons can hold CLI stderr or a judge's multi-line text, and names written in the eval suite can hold a newline too. A line
        # starting with ``` or # would open a code fence or a heading and swallow the rest of the report; the full text stays
        # in each trial's grade artifact.
        return " ".join(report_text.split())
