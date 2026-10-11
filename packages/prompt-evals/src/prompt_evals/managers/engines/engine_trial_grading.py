import asyncio
import logging
import time
from collections.abc import Iterable, Mapping
from typing import Final, assert_never, final

from prompt_evals.managers.configuration_providers.settings_models.grading_settings import GradingSettings
from prompt_evals.managers.engines.llm_processors.answer_facts_extraction_processor import LlmProcessorAnswerFactsExtraction
from prompt_evals.managers.engines.llm_processors.rubric_judgment_processor import LlmProcessorRubricJudgment
from prompt_evals.managers.engines.processors.check_outcome_diagnosis_processor import CheckOutcomeDiagnosisProcessor
from prompt_evals.managers.engines.processors.fact_check_grading_processor import FactCheckGradingProcessor
from prompt_evals.managers.engines.processors.judge_check_grading_processor import JudgeCheckGradingProcessor
from prompt_evals.managers.engines.processors.tool_use_check_grading_processor import ToolUseCheckGradingProcessor
from prompt_evals.managers.exceptions.grading_exceptions import GraderResponseBaseException
from prompt_evals.managers.exceptions.llm_session_exceptions import SINGLE_SESSION_FAILURE_TYPES
from prompt_evals.managers.exceptions.prompt_evals_exceptions import PromptEvalsTechnicalBaseException
from prompt_evals.managers.gateways.gateway_llm_protocol import GatewayLlmProtocol
from prompt_evals.managers.models.eval_suite_models import (
    AmountCheckDefinition,
    CheckDefinition,
    EvalCase,
    FactExtraction,
    FactValueCheckDefinition,
    JudgeCheckDefinition,
    ToolUseCheckDefinition,
)
from prompt_evals.managers.models.grading_models import (
    CheckOutcome,
    CheckStatus,
    ExtractedFacts,
    FactExtractionAttempt,
    FailedFactExtraction,
    FailedJudgment,
    GraderReports,
    JudgeVerdict,
    JudgmentAttempt,
    SucceededFactExtraction,
    SucceededJudgment,
    TrialGrade,
)
from prompt_evals.managers.models.trial_models import CompletedTrial, ErroredTrial, TrialIdentity, TrialRecord

GRADER_FAILURE_TYPES: Final[tuple[type[PromptEvalsTechnicalBaseException], ...]] = (*SINGLE_SESSION_FAILURE_TYPES, GraderResponseBaseException)


@final
class EngineTrialGrading:
    """Assert: grades every trial against every check. Graders run in their own sessions and never see the trial's sandbox."""

    def __init__(self, gateway_llm: GatewayLlmProtocol, grading_settings: GradingSettings, logger: logging.Logger) -> None:
        self._grading_settings: GradingSettings = grading_settings
        self._logger: logging.Logger = logger
        self._llm_processor_answer_facts_extraction: LlmProcessorAnswerFactsExtraction = LlmProcessorAnswerFactsExtraction(
            gateway_llm, grading_settings, logger.getChild("fact_extraction")
        )
        self._llm_processor_rubric_judgment: LlmProcessorRubricJudgment = LlmProcessorRubricJudgment(
            gateway_llm, grading_settings, logger.getChild("judgment")
        )

    async def grade_trials(
        self,
        check_definitions: tuple[CheckDefinition, ...],
        fact_extraction: FactExtraction,
        eval_cases: tuple[EvalCase, ...],
        trial_records: tuple[TrialRecord, ...],
    ) -> tuple[TrialGrade, ...]:
        eval_case_by_case_name: dict[str, EvalCase] = self._index_eval_cases_by_case_name(eval_cases)
        return await self._grade_trials_concurrently(check_definitions, fact_extraction, eval_case_by_case_name, trial_records)

    @staticmethod
    def _index_eval_cases_by_case_name(eval_cases: tuple[EvalCase, ...]) -> dict[str, EvalCase]:
        # Case names are unique (eval suite validation), and every trial was created from one of these cases.
        return {eval_case.case_name: eval_case for eval_case in eval_cases}

    async def _grade_trials_concurrently(
        self,
        check_definitions: tuple[CheckDefinition, ...],
        fact_extraction: FactExtraction,
        eval_case_by_case_name: Mapping[str, EvalCase],
        trial_records: tuple[TrialRecord, ...],
    ) -> tuple[TrialGrade, ...]:
        grading_slots: asyncio.Semaphore = asyncio.Semaphore(self._grading_settings.maximum_concurrent_gradings)
        trial_grade_tasks: list[asyncio.Task[TrialGrade]] = []
        # Callers expect the domain exception itself, not the task group's wrapper around it.
        try:
            async with asyncio.TaskGroup() as task_group:
                trial_grade_tasks = [
                    task_group.create_task(
                        self._grade_trial(
                            grading_slots,
                            check_definitions,
                            fact_extraction,
                            eval_case_by_case_name[trial_record.trial_identity.case_name],
                            trial_record,
                        )
                    )
                    for trial_record in trial_records
                ]
        except ExceptionGroup as grading_failures:
            raise grading_failures.exceptions[0] from grading_failures
        return tuple(trial_grade_task.result() for trial_grade_task in trial_grade_tasks)

    async def _grade_trial(
        self,
        grading_slots: asyncio.Semaphore,
        check_definitions: tuple[CheckDefinition, ...],
        fact_extraction: FactExtraction,
        eval_case: EvalCase,
        trial_record: TrialRecord,
    ) -> TrialGrade:
        trial_identity: TrialIdentity = trial_record.trial_identity
        match trial_record:
            case ErroredTrial(error_description=error_description):
                return TrialGrade(
                    trial_identity=trial_identity,
                    extracted_facts=None,
                    check_outcomes=tuple(
                        self._create_errored_outcome(check_definition, trial_identity, f"the trial did not complete: {error_description}")
                        for check_definition in check_definitions
                    ),
                    grading_duration_seconds=0.0,
                )
            case CompletedTrial():
                async with grading_slots:
                    # Timed inside the slot, so the grading time excludes waiting for another trial's graders to finish.
                    started_seconds: float = time.perf_counter()
                    self._logger.info(
                        "Grading: %s / %s / run %d", trial_identity.variant_name, trial_identity.case_name, trial_identity.repetition_number
                    )
                    grader_reports: GraderReports = GraderReports(
                        fact_extraction_attempt=await self._attempt_fact_extraction(fact_extraction, trial_record.llm_session_transcript.final_text),
                        judgment_attempt_by_check_name=await self._attempt_judgments(
                            check_definitions, trial_record.llm_session_transcript.final_text
                        ),
                    )
                fact_extraction_attempt: FactExtractionAttempt = grader_reports.fact_extraction_attempt
                check_outcomes: tuple[CheckOutcome, ...] = tuple(
                    self._grade_check(check_definition, trial_record, eval_case, grader_reports) for check_definition in check_definitions
                )
                return TrialGrade(
                    trial_identity=trial_identity,
                    extracted_facts=fact_extraction_attempt.extracted_facts if isinstance(fact_extraction_attempt, SucceededFactExtraction) else None,
                    check_outcomes=check_outcomes,
                    grading_duration_seconds=time.perf_counter() - started_seconds,
                )

    async def _attempt_fact_extraction(self, fact_extraction: FactExtraction, answer_text: str) -> FactExtractionAttempt:
        try:
            extracted_facts: ExtractedFacts = await self._llm_processor_answer_facts_extraction.extract_answer_facts(fact_extraction, answer_text)
        except GRADER_FAILURE_TYPES as grader_failure:
            # Only the fact-based checks depend on extraction; they are recorded as errored, the rest still run.
            return FailedFactExtraction(failure_description=grader_failure.message)
        return SucceededFactExtraction(extracted_facts=extracted_facts)

    async def _attempt_judgments(self, check_definitions: Iterable[CheckDefinition], answer_text: str) -> dict[str, JudgmentAttempt]:
        judgment_attempt_by_check_name: dict[str, JudgmentAttempt] = {}
        for check_definition in check_definitions:
            if not isinstance(check_definition, JudgeCheckDefinition):
                continue
            try:
                judge_verdict: JudgeVerdict = await self._llm_processor_rubric_judgment.judge_answer(check_definition.rubric, answer_text)
            except GRADER_FAILURE_TYPES as grader_failure:
                # A judge that cannot answer errors only its own check; the other checks are still graded.
                judgment_attempt_by_check_name[check_definition.check_name] = FailedJudgment(failure_description=grader_failure.message)
                continue
            judgment_attempt_by_check_name[check_definition.check_name] = SucceededJudgment(judge_verdict=judge_verdict)
        return judgment_attempt_by_check_name

    @staticmethod
    def _grade_check(
        check_definition: CheckDefinition, completed_trial: CompletedTrial, eval_case: EvalCase, grader_reports: GraderReports
    ) -> CheckOutcome:
        trial_identity: TrialIdentity = completed_trial.trial_identity
        match check_definition:
            case AmountCheckDefinition():
                return CheckOutcomeDiagnosisProcessor.diagnose_amount_check_outcome(
                    FactCheckGradingProcessor.grade_fact_check(
                        check_definition, grader_reports.fact_extraction_attempt, eval_case.expected_facts, trial_identity
                    ),
                    check_definition.fact_name,
                    grader_reports.fact_extraction_attempt,
                    eval_case.reference_ledger,
                )
            case FactValueCheckDefinition():
                return FactCheckGradingProcessor.grade_fact_check(
                    check_definition, grader_reports.fact_extraction_attempt, eval_case.expected_facts, trial_identity
                )
            case ToolUseCheckDefinition():
                return ToolUseCheckGradingProcessor.grade_tool_use_check(
                    check_definition, completed_trial.llm_session_transcript.tool_calls, trial_identity
                )
            case JudgeCheckDefinition():
                judgment_attempt: JudgmentAttempt = grader_reports.judgment_attempt_by_check_name[check_definition.check_name]
                return CheckOutcomeDiagnosisProcessor.diagnose_judge_check_outcome(
                    JudgeCheckGradingProcessor.grade_judge_check(check_definition, judgment_attempt, trial_identity),
                    judgment_attempt,
                    eval_case.reference_ledger,
                )
            case _:
                assert_never(check_definition)

    @staticmethod
    def _create_errored_outcome(check_definition: CheckDefinition, trial_identity: TrialIdentity, reason: str) -> CheckOutcome:
        return CheckOutcome(
            check_name=check_definition.check_name,
            trial_identity=trial_identity,
            check_status=CheckStatus.ERRORED,
            reason=reason,
            amount_discrepancy_diagnoses=(),
        )
