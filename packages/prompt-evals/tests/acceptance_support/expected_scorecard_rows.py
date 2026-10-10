from collections.abc import Iterable

from acceptance_support.asserters.scorecard_asserter import ExpectedScorecardRow
from acceptance_support.sample_eval_suite_builder import CHECK_NAMES_IN_SUITE_ORDER


def create_expected_rows_for_every_check(
    variant_name: str, trial_count: int, passed_count: int, errored_count: int = 0
) -> list[ExpectedScorecardRow]:
    return [
        ExpectedScorecardRow(
            check_name=check_name,
            variant_name=variant_name,
            trial_count=trial_count,
            passed_count=passed_count,
            errored_count=errored_count,
            meets_minimum_pass_rate=passed_count == trial_count,
        )
        for check_name in CHECK_NAMES_IN_SUITE_ORDER
    ]


def interleave_rows_by_check(*expected_rows_per_variant: Iterable[ExpectedScorecardRow]) -> tuple[ExpectedScorecardRow, ...]:
    return tuple(expected_row for expected_rows in zip(*expected_rows_per_variant, strict=True) for expected_row in expected_rows)
