import dataclasses
import json
import secrets
from pathlib import Path
from typing import Final

from prompt_evals import (
    CodingAssistant,
    DurationSummary,
    EffortLevel,
    Scorecard,
    ScorecardRow,
    ScorecardTiming,
    VariantTiming,
)
from prompt_evals_app.comparison_main import EXIT_CODE_INVALID_INPUT, EXIT_CODE_WRITTEN, run
from prompt_evals_app.scorecard_comparison_renderer import ScorecardComparisonRenderer
from prompt_evals_app.scorecard_summary_reader import ScorecardSummaryReader, VariantResult

COMPARISON_FILE_NAME: Final[str] = "scorecard_comparison.md"
SCORECARD_FILE_NAME: Final[str] = "scorecard.json"
REPETITIONS: Final[int] = 5


def create_random_text(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(4)}"


def create_run_folder_name(run_timestamp: str, model_name: str) -> str:
    return f"{run_timestamp}-claude_code-{model_name}-medium-{secrets.token_hex(3)}"


def create_scorecard_row(check_name: str, variant_name: str, passed_count: int) -> ScorecardRow:
    return ScorecardRow(
        check_name=check_name,
        description=create_random_text("description"),
        variant_name=variant_name,
        trial_count=REPETITIONS,
        passed_count=passed_count,
        errored_count=0,
        pass_rate=passed_count / REPETITIONS,
        minimum_pass_rate=0.8,
        is_gated=True,
        meets_minimum_pass_rate=passed_count >= 4,
        failure_reasons=(),
    )


def create_variant_timing(variant_name: str) -> VariantTiming:
    return VariantTiming(
        variant_name=variant_name,
        is_gated=True,
        trial_count=REPETITIONS,
        answer_duration_summary=DurationSummary(median_seconds=95.0, minimum_seconds=80.2, maximum_seconds=131.6, measured_trial_count=REPETITIONS),
        grading_duration_summary=DurationSummary(median_seconds=31.0, minimum_seconds=28.0, maximum_seconds=40.4, measured_trial_count=REPETITIONS),
        total_duration_summary=DurationSummary(median_seconds=126.0, minimum_seconds=110.0, maximum_seconds=170.0, measured_trial_count=REPETITIONS),
    )


def create_scorecard(model_name: str, variant_name: str, scorecard_rows: tuple[ScorecardRow, ...]) -> Scorecard:
    return Scorecard(
        eval_suite_name=create_random_text("suite"),
        coding_assistant=CodingAssistant.CLAUDE_CODE,
        model_name=model_name,
        effort_level=EffortLevel.MEDIUM,
        repetitions=REPETITIONS,
        scorecard_rows=scorecard_rows,
        failure_causes=(),
        scorecard_timing=ScorecardTiming(variant_timings=(create_variant_timing(variant_name),), trial_timings=()),
        passes_gate=all(scorecard_row.meets_minimum_pass_rate for scorecard_row in scorecard_rows),
    )


def write_scorecard(results_directory: Path, run_folder_name: str, scorecard: Scorecard) -> Path:
    # The evaluation writes scorecard.json as json.dumps(dataclasses.asdict(scorecard)), so the comparison reads the real field names.
    run_directory: Path = results_directory / run_folder_name
    run_directory.mkdir(parents=True)
    scorecard_path: Path = run_directory / SCORECARD_FILE_NAME
    scorecard_path.write_text(json.dumps(dataclasses.asdict(scorecard)), encoding="utf-8")
    return scorecard_path


def remove_scorecard_timing(scorecard_path: Path) -> None:
    # Scorecards written before timing was recorded have no scorecard_timing.
    scorecard_object: dict[str, object] = json.loads(scorecard_path.read_text(encoding="utf-8"))
    del scorecard_object["scorecard_timing"]
    scorecard_path.write_text(json.dumps(scorecard_object), encoding="utf-8")


class TestScorecardComparison:
    def test_ReadLatestVariantResults_WhenAConfigurationRanTwice_ThenOnlyItsNewestRunIsKept(self, tmp_path: Path) -> None:
        # Arrange
        variant_name: str = create_random_text("variant")
        model_name: str = create_random_text("model")
        other_model_name: str = create_random_text("model")
        newest_run_folder_name: str = create_run_folder_name("20261011T100000Z", model_name)
        older_run_folder_name: str = create_run_folder_name("20261010T100000Z", model_name)
        other_run_folder_name: str = create_run_folder_name("20261009T100000Z", other_model_name)
        scorecard_rows: tuple[ScorecardRow, ...] = (create_scorecard_row(create_random_text("check"), variant_name, REPETITIONS),)
        # The newest folder is written first, so neither creation nor modification order can stand in for the name order the
        # comparison relies on.
        write_scorecard(tmp_path, newest_run_folder_name, create_scorecard(model_name, variant_name, scorecard_rows))
        write_scorecard(tmp_path, older_run_folder_name, create_scorecard(model_name, variant_name, scorecard_rows))
        write_scorecard(tmp_path, other_run_folder_name, create_scorecard(other_model_name, variant_name, scorecard_rows))
        expected_run_folder_names: list[str] = sorted([newest_run_folder_name, other_run_folder_name])

        # Act
        actual_variant_results: tuple[VariantResult, ...] = ScorecardSummaryReader.read_latest_variant_results(tmp_path)

        # Assert
        actual_run_folder_names: list[str] = sorted(variant_result.run_folder_name for variant_result in actual_variant_results)
        assert actual_run_folder_names == expected_run_folder_names, f"expected {expected_run_folder_names}; actual {actual_run_folder_names}"

    def test_RenderComparison_WhenResultsHaveAndLackTimes_ThenEachRowShowsTheGateTheFailingChecksAndTheTimes(self, tmp_path: Path) -> None:
        # Arrange
        variant_name: str = create_random_text("variant")
        failing_check_name: str = create_random_text("check")
        timed_model_name: str = create_random_text("model")
        untimed_model_name: str = create_random_text("model")
        timed_run_folder_name: str = create_run_folder_name("20261011T100000Z", timed_model_name)
        untimed_run_folder_name: str = create_run_folder_name("20261009T100000Z", untimed_model_name)
        write_scorecard(
            tmp_path,
            timed_run_folder_name,
            create_scorecard(timed_model_name, variant_name, (create_scorecard_row(failing_check_name, variant_name, 0),)),
        )
        untimed_scorecard_rows: tuple[ScorecardRow, ...] = (create_scorecard_row(create_random_text("check"), variant_name, REPETITIONS),)
        remove_scorecard_timing(
            write_scorecard(tmp_path, untimed_run_folder_name, create_scorecard(untimed_model_name, variant_name, untimed_scorecard_rows))
        )
        expected_lines: list[str] = [
            (
                f"| claude_code | {timed_model_name} | medium | {variant_name} | {REPETITIONS} | ❌ failed | "
                f"{failing_check_name} 0/{REPETITIONS} | 0 | 1m 35s (1m 20s to 2m 12s) | 31s (28s to 40s) | 2m 06s (1m 50s to 2m 50s) | "
                f"`{timed_run_folder_name}` |"
            ),
            (
                f"| claude_code | {untimed_model_name} | medium | {variant_name} | {REPETITIONS} | ✅ passed | none | 0 | "
                f"not recorded | not recorded | not recorded | `{untimed_run_folder_name}` |"
            ),
        ]

        # Act
        actual_report: str = ScorecardComparisonRenderer.render_comparison(
            create_random_text("suite"), ScorecardSummaryReader.read_latest_variant_results(tmp_path)
        )

        # Assert
        missing_lines: list[str] = [expected_line for expected_line in expected_lines if expected_line not in actual_report.splitlines()]
        assert not missing_lines, f"expected the rows {missing_lines}; actual report:\n{actual_report}"

    def test_Run_WhenResultsFolderHoldsScorecards_ThenTheComparisonIsWrittenIntoThatFolder(self, tmp_path: Path) -> None:
        # Arrange
        variant_name: str = create_random_text("variant")
        model_name: str = create_random_text("model")
        scorecard_rows: tuple[ScorecardRow, ...] = (create_scorecard_row(create_random_text("check"), variant_name, REPETITIONS),)
        write_scorecard(tmp_path, create_run_folder_name("20261011T100000Z", model_name), create_scorecard(model_name, variant_name, scorecard_rows))
        expected_row_start: str = f"| claude_code | {model_name} | medium | {variant_name} |"
        expected_outcome: tuple[int, bool] = (EXIT_CODE_WRITTEN, True)

        # Act
        actual_exit_code: int = run([str(tmp_path)])

        # Assert
        comparison_path: Path = tmp_path / COMPARISON_FILE_NAME
        actual_outcome: tuple[int, bool] = (
            actual_exit_code,
            comparison_path.is_file() and expected_row_start in comparison_path.read_text(encoding="utf-8"),
        )
        assert actual_outcome == expected_outcome, (
            f"expected (exit code, comparison written with the row starting {expected_row_start!r}) {expected_outcome}; actual {actual_outcome}"
        )

    def test_Run_WhenAScorecardHoldsANonFiniteTime_ThenItExitsWithInvalidInputAndWritesNothing(self, tmp_path: Path) -> None:
        # Arrange
        variant_name: str = create_random_text("variant")
        model_name: str = create_random_text("model")
        scorecard_rows: tuple[ScorecardRow, ...] = (create_scorecard_row(create_random_text("check"), variant_name, REPETITIONS),)
        scorecard_path: Path = write_scorecard(
            tmp_path, create_run_folder_name("20261011T100000Z", model_name), create_scorecard(model_name, variant_name, scorecard_rows)
        )
        scorecard_object: dict[str, object] = json.loads(scorecard_path.read_text(encoding="utf-8"))
        non_finite_summary: dict[str, object] = {
            "median_seconds": float("nan"),
            "minimum_seconds": 1.0,
            "maximum_seconds": 2.0,
            "measured_trial_count": 1,
        }
        scorecard_object["scorecard_timing"] = {"variant_timings": [{"variant_name": variant_name, "answer_duration_summary": non_finite_summary}]}
        scorecard_path.write_text(json.dumps(scorecard_object), encoding="utf-8")
        expected_outcome: tuple[int, bool] = (EXIT_CODE_INVALID_INPUT, False)

        # Act
        actual_exit_code: int = run([str(tmp_path)])

        # Assert
        actual_outcome: tuple[int, bool] = (actual_exit_code, (tmp_path / COMPARISON_FILE_NAME).exists())
        assert actual_outcome == expected_outcome, f"expected (exit code, comparison written) {expected_outcome}; actual {actual_outcome}"
