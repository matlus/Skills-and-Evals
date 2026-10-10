"""The expense-analysis eval as a regression gate.

Arrange: the eval suite (prompts, the expense log and budget notes, the reference key's facts, the graders).
Act:     run every prompt variant `--eval-repetitions` times, each in a brand-new isolated session of `--eval-assistant`.
Assert:  every check on the gated (robust-tables-first) prompt reaches its minimum pass rate.

The standard prompt runs too, for comparison in scorecard.md, but does not decide pass or fail.
"""

from pathlib import Path
from typing import Final

import pytest
from prompt_eval_options import PromptEvalOptions

from prompt_evals import DomainFacade, EvaluationRequest, Scorecard, ScorecardRow
from prompt_evals_app.results_directory_writer import ResultsDirectoryWriter

EVAL_SUITE_DIRECTORY: Final[Path] = Path(__file__).resolve().parent
RESULTS_ROOT: Final[Path] = EVAL_SUITE_DIRECTORY.parents[1] / "results"


@pytest.mark.prompt_eval
class TestExpenseAnalysisPromptEval:
    async def test_ExpenseAnalysis_WhenEachPromptRunsRepeatedlyInIsolatedSessions_ThenEveryGatedCheckMeetsItsMinimumPassRate(
        self, prompt_eval_options: PromptEvalOptions
    ) -> None:
        # Arrange
        evaluation_request: EvaluationRequest = EvaluationRequest(
            eval_suite_directory=EVAL_SUITE_DIRECTORY,
            coding_assistant=prompt_eval_options.coding_assistant,
            model_name=prompt_eval_options.model_name,
            effort_level=prompt_eval_options.effort_level,
            repetitions=prompt_eval_options.repetitions,
        )
        results_directory_writer: ResultsDirectoryWriter = ResultsDirectoryWriter.create_for_run(
            RESULTS_ROOT,
            EVAL_SUITE_DIRECTORY.name,
            evaluation_request.coding_assistant,
            evaluation_request.model_name,
            evaluation_request.effort_level,
        )
        domain_facade: DomainFacade = DomainFacade()

        # Act
        actual_scorecard: Scorecard = await domain_facade.run_evaluation(evaluation_request, results_directory_writer.write_evaluation_artifact)

        # Assert
        actual_rows_below_minimum: list[ScorecardRow] = [
            scorecard_row for scorecard_row in actual_scorecard.scorecard_rows if scorecard_row.is_gated and not scorecard_row.meets_minimum_pass_rate
        ]
        scorecard_path: Path = results_directory_writer.run_directory / "scorecard.md"
        assert not actual_rows_below_minimum, (
            f"{len(actual_rows_below_minimum)} gated checks are below their minimum pass rate. Full scorecard: {scorecard_path}\n\n"
            + domain_facade.render_scorecard_report(actual_scorecard)
        )
