import asyncio
import logging
import time
from collections.abc import Iterable
from typing import Final, final

from prompt_evals.managers.configuration_providers.settings_models.trial_execution_settings import TrialExecutionSettings
from prompt_evals.managers.exceptions.llm_session_exceptions import SINGLE_SESSION_FAILURE_TYPES
from prompt_evals.managers.gateways.gateway_llm_protocol import GatewayLlmProtocol
from prompt_evals.managers.models.eval_suite_models import EvalCase, EvalSuite, PromptVariant, ToolKind
from prompt_evals.managers.models.evaluation_models import EffortLevel, EvaluationRequest
from prompt_evals.managers.models.llm_session_models import LlmSessionRequest, LlmSessionTranscript
from prompt_evals.managers.models.regrade_models import RecordedCompletedTrial, RecordedErroredTrial, RecordedTrial
from prompt_evals.managers.models.trial_models import CompletedTrial, ErroredTrial, TrialAssignment, TrialIdentity, TrialRecord

# The prompts say "attached"; in a CLI session the attachments are files in the working directory.
# Every variant receives the identical note, so it cannot favour one prompt over another.
ATTACHMENT_NOTE_TEMPLATE: Final[str] = "\n\n---\nAttached files (in the current working directory): {attached_file_names}\n"
MILLISECONDS_PER_SECOND: Final[int] = 1000


@final
class EngineTrialExecution:
    """Act: runs every selected prompt variant against every case, `repetitions` times, each in a fresh session."""

    def __init__(self, gateway_llm: GatewayLlmProtocol, trial_execution_settings: TrialExecutionSettings, logger: logging.Logger) -> None:
        self._gateway_llm: GatewayLlmProtocol = gateway_llm
        self._trial_execution_settings: TrialExecutionSettings = trial_execution_settings
        self._logger: logging.Logger = logger

    async def run_trials(self, eval_suite: EvalSuite, evaluation_request: EvaluationRequest) -> tuple[TrialRecord, ...]:
        trial_assignments: list[TrialAssignment] = self._compose_trial_assignments(eval_suite, evaluation_request)
        return await self._execute_trial_assignments(trial_assignments)

    def read_recorded_trials(self, recorded_trials: Iterable[RecordedTrial], model_name: str) -> tuple[TrialRecord, ...]:
        """The trials an earlier run recorded, read back as if they had just run; a recording that cannot be read is an errored trial."""
        return tuple(self._read_recorded_trial(recorded_trial, model_name) for recorded_trial in recorded_trials)

    def _read_recorded_trial(self, recorded_trial: RecordedTrial, model_name: str) -> TrialRecord:
        match recorded_trial:
            case RecordedErroredTrial(
                trial_identity=trial_identity, error_description=error_description, answer_duration_seconds=answer_duration_seconds
            ):
                return ErroredTrial(
                    trial_identity=trial_identity, error_description=error_description, answer_duration_seconds=answer_duration_seconds
                )
            case RecordedCompletedTrial(
                trial_identity=trial_identity, event_stream_text=event_stream_text, answer_duration_seconds=answer_duration_seconds
            ):
                try:
                    llm_session_transcript: LlmSessionTranscript = self._gateway_llm.read_recorded_session(event_stream_text, model_name)
                except SINGLE_SESSION_FAILURE_TYPES as single_session_failure:
                    return ErroredTrial(
                        trial_identity=trial_identity,
                        error_description=single_session_failure.message,
                        answer_duration_seconds=answer_duration_seconds,
                    )
                return CompletedTrial(
                    trial_identity=trial_identity,
                    llm_session_transcript=llm_session_transcript,
                    answer_duration_seconds=self._choose_recorded_answer_duration(
                        answer_duration_seconds, llm_session_transcript.duration_milliseconds
                    ),
                )

    @staticmethod
    def _choose_recorded_answer_duration(answer_duration_seconds: float | None, stream_duration_milliseconds: int | None) -> float | None:
        # Runs recorded before answer times were saved still have the duration some assistants report in their own event stream.
        if answer_duration_seconds is not None:
            return answer_duration_seconds
        if stream_duration_milliseconds is None:
            return None
        return stream_duration_milliseconds / MILLISECONDS_PER_SECOND

    @staticmethod
    def _compose_trial_assignments(eval_suite: EvalSuite, evaluation_request: EvaluationRequest) -> list[TrialAssignment]:
        selected_prompt_variants: list[PromptVariant] = EngineTrialExecution._select_prompt_variants(
            eval_suite.prompt_variants, evaluation_request.variant_names
        )
        return [
            TrialAssignment(
                trial_identity=TrialIdentity(
                    variant_name=prompt_variant.variant_name, case_name=eval_case.case_name, repetition_number=repetition_number
                ),
                llm_session_request=EngineTrialExecution._compose_llm_session_request(
                    prompt_variant, eval_case, eval_suite.trial_tool_kinds, evaluation_request.model_name, evaluation_request.effort_level
                ),
            )
            for prompt_variant in selected_prompt_variants
            for eval_case in eval_suite.eval_cases
            for repetition_number in range(1, evaluation_request.repetitions + 1)
        ]

    @staticmethod
    def _select_prompt_variants(prompt_variants: tuple[PromptVariant, ...], variant_names: tuple[str, ...]) -> list[PromptVariant]:
        # An empty selection means every variant the eval suite defines.
        return [prompt_variant for prompt_variant in prompt_variants if not variant_names or prompt_variant.variant_name in variant_names]

    @staticmethod
    def _compose_llm_session_request(
        prompt_variant: PromptVariant,
        eval_case: EvalCase,
        trial_tool_kinds: tuple[ToolKind, ...],
        model_name: str,
        effort_level: EffortLevel,
    ) -> LlmSessionRequest:
        attached_file_names: str = ", ".join(input_file.file_name for input_file in eval_case.input_files)
        return LlmSessionRequest(
            prompt_text=prompt_variant.prompt_text.rstrip() + ATTACHMENT_NOTE_TEMPLATE.format(attached_file_names=attached_file_names),
            input_files=eval_case.input_files,
            model_name=model_name,
            effort_level=effort_level,
            tool_kinds=trial_tool_kinds,
            structured_output_schema=None,
        )

    async def _execute_trial_assignments(self, trial_assignments: Iterable[TrialAssignment]) -> tuple[TrialRecord, ...]:
        trial_slots: asyncio.Semaphore = asyncio.Semaphore(self._trial_execution_settings.maximum_concurrent_trials)
        trial_record_tasks: list[asyncio.Task[TrialRecord]] = []
        # A task group cancels the remaining trials (and kills their processes) if one fails unexpectedly.
        # Callers expect the domain exception itself, not the group that wraps it.
        try:
            async with asyncio.TaskGroup() as task_group:
                trial_record_tasks = [
                    task_group.create_task(self._run_trial(trial_slots, trial_assignment)) for trial_assignment in trial_assignments
                ]
        except ExceptionGroup as trial_failures:
            raise trial_failures.exceptions[0] from trial_failures
        return tuple(trial_record_task.result() for trial_record_task in trial_record_tasks)

    async def _run_trial(self, trial_slots: asyncio.Semaphore, trial_assignment: TrialAssignment) -> TrialRecord:
        trial_identity: TrialIdentity = trial_assignment.trial_identity
        async with trial_slots:
            self._logger.info(
                "Trial started: %s / %s / run %d", trial_identity.variant_name, trial_identity.case_name, trial_identity.repetition_number
            )
            # Timed inside the slot, so the answer time excludes waiting for another trial to finish.
            started_seconds: float = time.perf_counter()
            try:
                llm_session_transcript: LlmSessionTranscript = await self._gateway_llm.run_session(trial_assignment.llm_session_request)
            except SINGLE_SESSION_FAILURE_TYPES as single_session_failure:
                # A run that crashes or times out is itself an eval result: it counts as failing every
                # check. Raising here would throw away every other run in the evaluation.
                self._logger.info(
                    "Trial errored: %s / %s / run %d", trial_identity.variant_name, trial_identity.case_name, trial_identity.repetition_number
                )
                return ErroredTrial(
                    trial_identity=trial_identity,
                    error_description=single_session_failure.message,
                    answer_duration_seconds=time.perf_counter() - started_seconds,
                )
            answer_duration_seconds: float = time.perf_counter() - started_seconds
        self._logger.info(
            "Trial finished: %s / %s / run %d in %.0fs",
            trial_identity.variant_name,
            trial_identity.case_name,
            trial_identity.repetition_number,
            answer_duration_seconds,
        )
        return CompletedTrial(
            trial_identity=trial_identity, llm_session_transcript=llm_session_transcript, answer_duration_seconds=answer_duration_seconds
        )
