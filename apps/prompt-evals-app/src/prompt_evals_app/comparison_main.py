import argparse
import io
import logging
import sys
from pathlib import Path
from typing import Final

from prompt_evals_app.scorecard_comparison_renderer import ScorecardComparisonRenderer
from prompt_evals_app.scorecard_summary_reader import ScorecardSummaryReader, VariantResult
from prompt_evals_app.scorecard_summary_unreadable_error import ScorecardSummaryUnreadableError

EXIT_CODE_WRITTEN: Final[int] = 0
EXIT_CODE_INVALID_INPUT: Final[int] = 2
EXIT_CODE_ENVIRONMENT_FAILURE: Final[int] = 3
COMPARISON_FILE_NAME: Final[str] = "scorecard_comparison.md"

LOGGER: Final[logging.Logger] = logging.getLogger("prompt_evals_app.comparison")


def parse_arguments(command_line_arguments: list[str]) -> argparse.Namespace:
    argument_parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="prompt_evals_compare",
        description=(
            f"Compare the newest run of every assistant, model, effort and prompt variant in one eval suite's results folder, and "
            f"write the table to {COMPARISON_FILE_NAME} in that folder."
        ),
    )
    argument_parser.add_argument(
        "results_directory", type=Path, help="Folder that holds the eval suite's run folders, e.g. results/pwi/expense_analysis"
    )
    return argument_parser.parse_args(command_line_arguments)


def run(command_line_arguments: list[str]) -> int:
    results_directory: Path = parse_arguments(command_line_arguments).results_directory
    if not results_directory.is_dir():
        LOGGER.error("The results folder does not exist | results_directory=%s", results_directory)
        return EXIT_CODE_INVALID_INPUT
    try:
        variant_results: tuple[VariantResult, ...] = ScorecardSummaryReader.read_latest_variant_results(results_directory)
    except ScorecardSummaryUnreadableError as scorecard_summary_unreadable_error:
        LOGGER.error("A scorecard cannot be compared: %s | results_directory=%s", scorecard_summary_unreadable_error, results_directory)
        return EXIT_CODE_INVALID_INPUT
    comparison_report: str = ScorecardComparisonRenderer.render_comparison(results_directory.resolve().name, variant_results)
    comparison_path: Path = results_directory / COMPARISON_FILE_NAME
    try:
        comparison_path.write_text(comparison_report, encoding="utf-8")
        sys.stdout.write(comparison_report)
        sys.stdout.write(f"\nWritten to: {comparison_path.resolve()}\n")
    except OSError:
        LOGGER.critical("The comparison could not be written | comparison_path=%s", comparison_path, exc_info=True)
        return EXIT_CODE_ENVIRONMENT_FAILURE
    return EXIT_CODE_WRITTEN


def main() -> None:
    # The table contains marks such as the check mark; a redirected Windows console would otherwise encode with cp1252.
    for standard_stream in (sys.stdout, sys.stderr):
        if isinstance(standard_stream, io.TextIOWrapper):
            standard_stream.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s", stream=sys.stderr)
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
