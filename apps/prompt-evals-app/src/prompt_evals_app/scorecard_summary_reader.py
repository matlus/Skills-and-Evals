from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Final, final

from prompt_evals_app.scorecard_document_resources import (
    DurationRangeResource,
    ScorecardDocumentResource,
    ScorecardRowResource,
    VariantTimingResource,
)
from prompt_evals_app.scorecard_summary_exceptions import ScorecardSummaryNotUtf8Exception, ScorecardSummaryReadFailedException
from prompt_evals_app.validator_scorecard_document_resource import ValidatorScorecardDocumentResource

TEXT_ENCODING: Final[str] = "utf-8"
SCORECARD_FILE_NAME: Final[str] = "scorecard.json"

type ConfigurationKey = tuple[str, str, str, str]


@dataclass(frozen=True)
class VariantResult:
    """One prompt variant's result in one run folder. `passes_gate` is the evaluation's own gate decision; a duration
    range is None when that run recorded no such time."""

    run_folder_name: str
    coding_assistant: str
    model_name: str
    effort_level: str
    variant_name: str
    is_gated: bool
    passes_gate: bool
    trial_count: int
    checks_below_minimum: tuple[str, ...]
    errored_check_count: int
    answer_duration_range: DurationRangeResource | None
    grading_duration_range: DurationRangeResource | None
    total_duration_range: DurationRangeResource | None

    @property
    def configuration_key(self) -> ConfigurationKey:
        return (self.coding_assistant, self.model_name, self.effort_level, self.variant_name)


@final
class ScorecardSummaryReader:
    """Reads the scorecard.json of every run folder in one eval suite's results folder and keeps, for each assistant, model,
    effort and prompt variant, the newest run that measured it."""

    @staticmethod
    def read_latest_variant_results(results_directory: Path) -> tuple[VariantResult, ...]:
        variant_results: list[VariantResult] = [
            variant_result
            for scorecard_path in ScorecardSummaryReader._find_scorecard_paths(results_directory)
            for variant_result in ScorecardSummaryReader._read_variant_results(scorecard_path)
        ]
        return ScorecardSummaryReader._keep_newest_per_configuration(variant_results)

    @staticmethod
    def _find_scorecard_paths(results_directory: Path) -> list[Path]:
        # Run folder names start with their UTC start time, so name order is start order.
        return sorted(results_directory.glob(f"*/{SCORECARD_FILE_NAME}"))

    @staticmethod
    def _keep_newest_per_configuration(variant_results: Iterable[VariantResult]) -> tuple[VariantResult, ...]:
        # The results arrive oldest first, so a later run of a configuration replaces an earlier one.
        newest_variant_result_by_configuration_key: dict[ConfigurationKey, VariantResult] = {
            variant_result.configuration_key: variant_result for variant_result in variant_results
        }
        return tuple(sorted(newest_variant_result_by_configuration_key.values(), key=lambda variant_result: variant_result.configuration_key))

    @staticmethod
    def _read_variant_results(scorecard_path: Path) -> list[VariantResult]:
        scorecard_document_resource: ScorecardDocumentResource = ValidatorScorecardDocumentResource.parse_scorecard_document(
            ScorecardSummaryReader._read_scorecard_text(scorecard_path), scorecard_path
        )
        variant_names: list[str] = list(
            dict.fromkeys(scorecard_row_resource.variant_name for scorecard_row_resource in scorecard_document_resource.scorecard_rows)
        )
        return [
            ScorecardSummaryReader._create_variant_result(scorecard_path.parent.name, scorecard_document_resource, variant_name)
            for variant_name in variant_names
        ]

    @staticmethod
    def _read_scorecard_text(scorecard_path: Path) -> str:
        try:
            return scorecard_path.read_text(encoding=TEXT_ENCODING)
        except UnicodeDecodeError as not_utf8_text:
            raise ScorecardSummaryNotUtf8Exception(scorecard_path, str(not_utf8_text)) from not_utf8_text
        except OSError as read_failure:
            raise ScorecardSummaryReadFailedException(scorecard_path, str(read_failure)) from read_failure

    @staticmethod
    def _create_variant_result(run_folder_name: str, scorecard_document_resource: ScorecardDocumentResource, variant_name: str) -> VariantResult:
        variant_rows: list[ScorecardRowResource] = [
            scorecard_row_resource
            for scorecard_row_resource in scorecard_document_resource.scorecard_rows
            if scorecard_row_resource.variant_name == variant_name
        ]
        variant_timing_resource: VariantTimingResource | None = next(
            (
                variant_timing_resource
                for variant_timing_resource in scorecard_document_resource.variant_timings
                if variant_timing_resource.variant_name == variant_name
            ),
            None,
        )
        return VariantResult(
            run_folder_name=run_folder_name,
            coding_assistant=scorecard_document_resource.coding_assistant,
            model_name=scorecard_document_resource.model_name,
            effort_level=scorecard_document_resource.effort_level,
            variant_name=variant_name,
            is_gated=variant_rows[0].is_gated,
            passes_gate=scorecard_document_resource.passes_gate,
            trial_count=variant_rows[0].trial_count,
            checks_below_minimum=tuple(
                f"{variant_row.check_name} {variant_row.passed_count}/{variant_row.trial_count}"
                for variant_row in variant_rows
                if not variant_row.meets_minimum_pass_rate
            ),
            errored_check_count=sum(variant_row.errored_count for variant_row in variant_rows),
            answer_duration_range=None if variant_timing_resource is None else variant_timing_resource.answer_duration_range,
            grading_duration_range=None if variant_timing_resource is None else variant_timing_resource.grading_duration_range,
            total_duration_range=None if variant_timing_resource is None else variant_timing_resource.total_duration_range,
        )
