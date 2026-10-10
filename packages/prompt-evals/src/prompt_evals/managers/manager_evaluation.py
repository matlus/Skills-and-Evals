import logging
from typing import Final, final

from prompt_evals.managers.artifact_emitters.evaluation_artifact_emitter import EvaluationArtifactEmitter
from prompt_evals.managers.configuration_providers.configuration_provider import ConfigurationProvider
from prompt_evals.managers.configuration_providers.settings_models.grading_settings import GradingSettings
from prompt_evals.managers.configuration_providers.settings_models.trial_execution_settings import TrialExecutionSettings
from prompt_evals.managers.data_managers.data_manager_eval_suite import DataManagerEvalSuite
from prompt_evals.managers.engines.engine_trial_execution import EngineTrialExecution
from prompt_evals.managers.engines.engine_trial_grading import EngineTrialGrading
from prompt_evals.managers.models.artifact_models import EvaluationArtifactCallback
from prompt_evals.managers.models.eval_suite_models import EvalSuite
from prompt_evals.managers.models.evaluation_models import EvaluationRequest, TrialRunDescription
from prompt_evals.managers.models.grading_models import TrialGrade
from prompt_evals.managers.models.regrade_models import RegradeRequest
from prompt_evals.managers.models.scorecard_models import Scorecard
from prompt_evals.managers.models.trial_models import TrialRecord
from prompt_evals.managers.processors.scorecard_aggregation_processor import ScorecardAggregationProcessor
from prompt_evals.managers.processors.scorecard_report_rendering_processor import ScorecardReportRenderingProcessor
from prompt_evals.managers.service_locators.service_locator_base import ServiceLocatorBase
from prompt_evals.managers.validators.validator_evaluation_request import ValidatorEvaluationRequest
from prompt_evals.managers.validators.validator_scorecard import ValidatorScorecard

LOGGER_NAME: Final[str] = "prompt_evals"


@final
class ManagerEvaluation:
    def __init__(self, service_locator: ServiceLocatorBase) -> None:
        configuration_provider: ConfigurationProvider = service_locator.get_configuration_provider()
        grading_settings: GradingSettings = configuration_provider.get_grading_settings()

        logger: logging.Logger = logging.getLogger(LOGGER_NAME)
        self._service_locator: ServiceLocatorBase = service_locator
        self._trial_execution_settings: TrialExecutionSettings = configuration_provider.get_trial_execution_settings()
        self._trials_logger: logging.Logger = logger.getChild("trials")
        self._data_manager_eval_suite: DataManagerEvalSuite = DataManagerEvalSuite()
        # Graders always run in the configured grader assistant; only the trials use the requested one.
        self._engine_trial_grading: EngineTrialGrading = EngineTrialGrading(
            service_locator.create_gateway_llm(grading_settings.grader_coding_assistant), grading_settings, logger.getChild("grading")
        )

    async def run_evaluation(self, evaluation_request: EvaluationRequest, evaluation_artifact_callback: EvaluationArtifactCallback) -> Scorecard:
        ValidatorEvaluationRequest.validate(evaluation_request)
        eval_suite: EvalSuite = self._data_manager_eval_suite.load_eval_suite(evaluation_request.eval_suite_directory)
        ValidatorEvaluationRequest.validate_variant_names(evaluation_request, eval_suite)

        engine_trial_execution: EngineTrialExecution = EngineTrialExecution(
            self._service_locator.create_gateway_llm(evaluation_request.coding_assistant), self._trial_execution_settings, self._trials_logger
        )
        trial_records: tuple[TrialRecord, ...] = await engine_trial_execution.run_trials(eval_suite, evaluation_request)
        return await self._grade_and_score(
            eval_suite,
            trial_records,
            TrialRunDescription(
                coding_assistant=evaluation_request.coding_assistant,
                model_name=evaluation_request.model_name,
                effort_level=evaluation_request.effort_level,
                repetitions=evaluation_request.repetitions,
            ),
            evaluation_artifact_callback,
        )

    async def regrade_evaluation(self, regrade_request: RegradeRequest, evaluation_artifact_callback: EvaluationArtifactCallback) -> Scorecard:
        ValidatorEvaluationRequest.validate_regrade_request(regrade_request)
        eval_suite: EvalSuite = self._data_manager_eval_suite.load_eval_suite(regrade_request.eval_suite_directory)
        ValidatorEvaluationRequest.validate_recorded_trial_names(regrade_request, eval_suite)

        engine_trial_execution: EngineTrialExecution = EngineTrialExecution(
            self._service_locator.create_gateway_llm(regrade_request.coding_assistant), self._trial_execution_settings, self._trials_logger
        )
        trial_records: tuple[TrialRecord, ...] = engine_trial_execution.read_recorded_trials(
            regrade_request.recorded_trials, regrade_request.model_name
        )
        return await self._grade_and_score(
            eval_suite,
            trial_records,
            TrialRunDescription(
                coding_assistant=regrade_request.coding_assistant,
                model_name=regrade_request.model_name,
                effort_level=regrade_request.effort_level,
                repetitions=max(recorded_trial.trial_identity.repetition_number for recorded_trial in regrade_request.recorded_trials),
            ),
            evaluation_artifact_callback,
        )

    async def _grade_and_score(
        self,
        eval_suite: EvalSuite,
        trial_records: tuple[TrialRecord, ...],
        trial_run_description: TrialRunDescription,
        evaluation_artifact_callback: EvaluationArtifactCallback,
    ) -> Scorecard:
        # Trial artifacts are emitted again on a regrade too, so every run folder holds the answers its grades refer to.
        EvaluationArtifactEmitter.emit_trial_records(evaluation_artifact_callback, trial_records)

        trial_grades: tuple[TrialGrade, ...] = await self._engine_trial_grading.grade_trials(
            eval_suite.check_definitions, eval_suite.fact_extraction, eval_suite.eval_cases, trial_records
        )
        EvaluationArtifactEmitter.emit_trial_grades(evaluation_artifact_callback, trial_grades)

        scorecard: Scorecard = ScorecardAggregationProcessor.aggregate_scorecard(eval_suite, trial_run_description, trial_grades)
        EvaluationArtifactEmitter.emit_scorecard(
            evaluation_artifact_callback, scorecard, ScorecardReportRenderingProcessor.render_scorecard_report(scorecard)
        )
        return scorecard

    def render_scorecard_report(self, scorecard: Scorecard) -> str:
        ValidatorScorecard.validate(scorecard)
        return ScorecardReportRenderingProcessor.render_scorecard_report(scorecard)
