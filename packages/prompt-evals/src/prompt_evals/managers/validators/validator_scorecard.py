import math
from itertools import groupby
from typing import final

from prompt_evals.managers.exceptions.scorecard_exceptions import ScorecardValidationException
from prompt_evals.managers.models.scorecard_models import Scorecard, ScorecardRow


@final
class ValidatorScorecard:
    """The layout the report renderer relies on: one consecutive group of rows per check, every group listing the same
    variants in the same order, and rates between 0 and 1. A scorecard from run_evaluation always has it."""

    @staticmethod
    def validate(scorecard: Scorecard) -> None:
        validation_problems: list[str] = [
            *ValidatorScorecard._find_rate_problems(scorecard),
            *ValidatorScorecard._find_layout_problems(scorecard),
        ]
        if validation_problems:
            raise ScorecardValidationException(validation_problems)

    @staticmethod
    def _find_rate_problems(scorecard: Scorecard) -> list[str]:
        return [
            f"row '{scorecard_row.check_name}' / '{scorecard_row.variant_name}' has a {rate_name} of {rate_value} (expected 0 to 1)"
            for scorecard_row in scorecard.scorecard_rows
            for rate_name, rate_value in (("pass_rate", scorecard_row.pass_rate), ("minimum_pass_rate", scorecard_row.minimum_pass_rate))
            if not math.isfinite(rate_value) or not 0 <= rate_value <= 1
        ]

    @staticmethod
    def _find_layout_problems(scorecard: Scorecard) -> list[str]:
        rows_per_check: list[list[ScorecardRow]] = [
            list(check_rows) for _, check_rows in groupby(scorecard.scorecard_rows, key=lambda scorecard_row: scorecard_row.check_name)
        ]
        if not rows_per_check:
            return []
        layout_problems: list[str] = ValidatorScorecard._find_split_check_groups(rows_per_check)
        expected_variant_names: list[str] = [scorecard_row.variant_name for scorecard_row in rows_per_check[0]]
        actual_variant_names: list[str]
        for check_rows in rows_per_check[1:]:
            actual_variant_names = [check_row.variant_name for check_row in check_rows]
            if actual_variant_names != expected_variant_names:
                layout_problems.append(
                    f"check '{check_rows[0].check_name}' lists variants {actual_variant_names}, expected {expected_variant_names} in that order"
                )
        return layout_problems

    @staticmethod
    def _find_split_check_groups(rows_per_check: list[list[ScorecardRow]]) -> list[str]:
        group_check_names: list[str] = [check_rows[0].check_name for check_rows in rows_per_check]
        return [
            f"the rows of check '{check_name}' are not consecutive"
            for check_name in dict.fromkeys(group_check_names)
            if group_check_names.count(check_name) > 1
        ]
