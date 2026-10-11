import argparse
import asyncio
import io
import logging
import sys
from pathlib import Path
from typing import Final

from prompt_evals import (
    CodingAssistant,
    DomainFacade,
    EffortLevel,
    EvaluationRequest,
    PromptEvalsBusinessBaseException,
    PromptEvalsTechnicalBaseException,
    RegradeRequest,
    Scorecard,
)
from prompt_evals_app.recorded_run_reader import RecordedRun, RecordedRunReader
from prompt_evals_app.results_directory_writer import ResultsDirectoryWriter

EXIT_CODE_GATE_PASSED: Final[int] = 0
EXIT_CODE_GATE_FAILED: Final[int] = 1
EXIT_CODE_INVALID_INPUT: Final[int] = 2
EXIT_CODE_ENVIRONMENT_FAILURE: Final[int] = 3

LOGGER: Final[logging.Logger] = logging.getLogger("prompt_evals_app")


def parse_arguments(command_line_arguments: list[str]) -> argparse.Namespace:
    argument_parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="prompt_evals_app",
        description="Run an eval suite: every prompt variant x every case x N isolated coding-assistant sessions, then grade and score them.",
    )
    argument_parser.add_argument("eval_suite_directory", type=Path, help="Folder that contains eval_suite.json, e.g. evals/expense_analysis")
    argument_parser.add_argument(
        "--assistant",
        default=CodingAssistant.CLAUDE_CODE.value,
        choices=[coding_assistant.value for coding_assistant in CodingAssistant],
        help="Coding assistant the trials run in. Default: claude_code",
    )
    argument_parser.add_argument(
        "--model", default="sonnet", help="Model for the trials (alias or full name; for codex e.g. gpt-6.1-sol). Default: sonnet"
    )
    argument_parser.add_argument("--effort", default=EffortLevel.MEDIUM.value, choices=[effort_level.value for effort_level in EffortLevel])
    argument_parser.add_argument("--repetitions", type=int, default=3, help="Isolated runs per variant per case. Default: 3")
    argument_parser.add_argument("--variant", action="append", default=[], help="Run only this variant (repeatable). Default: all variants")
    argument_parser.add_argument(
        "--results-root", type=Path, default=Path("results"), help="Run folders go in <results root>/pwi/<eval suite>/. Default: ./results"
    )
    argument_parser.add_argument(
        "--regrade",
        type=Path,
        metavar="RUN_DIRECTORY",
        help=(
            "Grade the recorded trials of an earlier run again with the eval suite's current graders and reference key, into a new "
            "run folder. No trial runs again. The model and effort come from that run's scorecard.json, and so does the assistant "
            "when the scorecard records it (otherwise --assistant)."
        ),
    )
    return argument_parser.parse_args(command_line_arguments)


async def run(command_line_arguments: list[str]) -> int:
    parsed_arguments: argparse.Namespace = parse_arguments(command_line_arguments)
    if parsed_arguments.regrade is not None:
        return await regrade(parsed_arguments)
    evaluation_request: EvaluationRequest = EvaluationRequest(
        eval_suite_directory=parsed_arguments.eval_suite_directory,
        coding_assistant=CodingAssistant(parsed_arguments.assistant),
        model_name=parsed_arguments.model,
        effort_level=EffortLevel(parsed_arguments.effort),
        repetitions=parsed_arguments.repetitions,
        variant_names=tuple(parsed_arguments.variant),
    )
    results_directory_writer: ResultsDirectoryWriter = ResultsDirectoryWriter.create_for_run(
        parsed_arguments.results_root,
        # resolve() first: for an eval suite given as '.' or '..' the unresolved name is empty or escapes the results root.
        evaluation_request.eval_suite_directory.resolve().name,
        evaluation_request.coding_assistant,
        evaluation_request.model_name,
        evaluation_request.effort_level,
    )
    request_context: str = (
        f"suite={evaluation_request.eval_suite_directory} assistant={evaluation_request.coding_assistant} model={evaluation_request.model_name} "
        f"effort={evaluation_request.effort_level} repetitions={evaluation_request.repetitions} "
        f"variants={list(evaluation_request.variant_names) or 'all'} "
        f"run_directory={results_directory_writer.run_directory}"
    )
    try:
        # Constructing the facade reads configuration, which can fail; it belongs inside the boundary.
        domain_facade: DomainFacade = DomainFacade()
        scorecard: Scorecard = await domain_facade.run_evaluation(evaluation_request, results_directory_writer.write_evaluation_artifact)
    except PromptEvalsBusinessBaseException as business_exception:
        # The caller must fix their input; a traceback would add nothing.
        LOGGER.error("%s | %s | context=%s", business_exception.message, request_context, business_exception.contextual_data_by_name)
        return EXIT_CODE_INVALID_INPUT
    except PromptEvalsTechnicalBaseException as technical_exception:
        LOGGER.exception("The evaluation could not run | %s | context=%s", request_context, technical_exception.contextual_data_by_name)
        return EXIT_CODE_ENVIRONMENT_FAILURE
    except Exception:
        LOGGER.critical("Unexpected failure | %s", request_context, exc_info=True)
        return EXIT_CODE_ENVIRONMENT_FAILURE
    return report_scorecard(domain_facade, scorecard, results_directory_writer, request_context)


async def regrade(parsed_arguments: argparse.Namespace) -> int:
    source_run_directory: Path = parsed_arguments.regrade
    try:
        recorded_run: RecordedRun = RecordedRunReader.read_recorded_run(source_run_directory, CodingAssistant(parsed_arguments.assistant))
    except PromptEvalsBusinessBaseException as business_exception:
        LOGGER.error(
            "The run to regrade is not one this app wrote: %s | run_directory=%s | context=%s",
            business_exception.message,
            source_run_directory,
            business_exception.contextual_data_by_name,
        )
        return EXIT_CODE_INVALID_INPUT
    except PromptEvalsTechnicalBaseException as technical_exception:
        LOGGER.error(
            "The run to regrade could not be read: %s | run_directory=%s | context=%s",
            technical_exception.message,
            source_run_directory,
            technical_exception.contextual_data_by_name,
        )
        return EXIT_CODE_ENVIRONMENT_FAILURE
    regrade_request: RegradeRequest = RegradeRequest(
        eval_suite_directory=parsed_arguments.eval_suite_directory,
        coding_assistant=recorded_run.coding_assistant,
        model_name=recorded_run.model_name,
        effort_level=recorded_run.effort_level,
        recorded_trials=recorded_run.recorded_trials,
    )
    results_directory_writer: ResultsDirectoryWriter = ResultsDirectoryWriter.create_for_regrade(
        parsed_arguments.results_root,
        regrade_request.eval_suite_directory.resolve().name,
        regrade_request.coding_assistant,
        regrade_request.model_name,
        regrade_request.effort_level,
    )
    request_context: str = (
        f"suite={regrade_request.eval_suite_directory} regrading={source_run_directory} assistant={regrade_request.coding_assistant} "
        f"model={regrade_request.model_name} effort={regrade_request.effort_level} trials={len(regrade_request.recorded_trials)} "
        f"run_directory={results_directory_writer.run_directory}"
    )
    try:
        domain_facade: DomainFacade = DomainFacade()
        results_directory_writer.write_regraded_from(source_run_directory)
        scorecard: Scorecard = await domain_facade.regrade_evaluation(regrade_request, results_directory_writer.write_evaluation_artifact)
    except PromptEvalsBusinessBaseException as business_exception:
        LOGGER.error("%s | %s | context=%s", business_exception.message, request_context, business_exception.contextual_data_by_name)
        return EXIT_CODE_INVALID_INPUT
    except PromptEvalsTechnicalBaseException as technical_exception:
        LOGGER.exception("The regrade could not run | %s | context=%s", request_context, technical_exception.contextual_data_by_name)
        return EXIT_CODE_ENVIRONMENT_FAILURE
    except Exception:
        LOGGER.critical("Unexpected failure | %s", request_context, exc_info=True)
        return EXIT_CODE_ENVIRONMENT_FAILURE
    return report_scorecard(domain_facade, scorecard, results_directory_writer, request_context)


def report_scorecard(
    domain_facade: DomainFacade, scorecard: Scorecard, results_directory_writer: ResultsDirectoryWriter, request_context: str
) -> int:
    try:
        sys.stdout.write(domain_facade.render_scorecard_report(scorecard))
        sys.stdout.write(f"\nArtifacts: {results_directory_writer.run_directory.resolve()}\n")
    except Exception:
        # An escaping exception (for example a broken stdout pipe) would exit with the interpreter's status 1, which reads as
        # a failed gate. scorecard.md is already in the run directory.
        LOGGER.critical("The scorecard could not be written to standard output | %s", request_context, exc_info=True)
        return EXIT_CODE_ENVIRONMENT_FAILURE
    return EXIT_CODE_GATE_PASSED if scorecard.passes_gate else EXIT_CODE_GATE_FAILED


def main() -> None:
    # The report contains marks such as the check mark; a redirected Windows console would otherwise encode with cp1252,
    # fail after the whole evaluation ran, and exit with the gate-failed code.
    for standard_stream in (sys.stdout, sys.stderr):
        if isinstance(standard_stream, io.TextIOWrapper):
            standard_stream.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s", stream=sys.stderr)
    sys.exit(asyncio.run(run(sys.argv[1:])))


if __name__ == "__main__":
    main()
