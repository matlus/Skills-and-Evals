from typing import final

from prompt_evals.managers.manager_evaluation import ManagerEvaluation
from prompt_evals.managers.models.artifact_models import EvaluationArtifactCallback
from prompt_evals.managers.models.evaluation_models import EvaluationRequest
from prompt_evals.managers.models.regrade_models import RegradeRequest
from prompt_evals.managers.models.scorecard_models import Scorecard
from prompt_evals.managers.service_locators.service_locator_base import ServiceLocatorBase
from prompt_evals.managers.service_locators.service_locator_production import ServiceLocatorProduction


@final
class DomainFacade:
    """Public entry point: evaluate prompt variants against an eval suite, or regrade an earlier run, and report pass rates."""

    def __init__(self, service_locator: ServiceLocatorBase | None = None) -> None:
        if service_locator is None:
            service_locator = ServiceLocatorProduction()
        self._manager_evaluation: ManagerEvaluation = ManagerEvaluation(service_locator)

    async def run_evaluation(self, evaluation_request: EvaluationRequest, evaluation_artifact_callback: EvaluationArtifactCallback) -> Scorecard:
        return await self._manager_evaluation.run_evaluation(evaluation_request, evaluation_artifact_callback)

    async def regrade_evaluation(self, regrade_request: RegradeRequest, evaluation_artifact_callback: EvaluationArtifactCallback) -> Scorecard:
        """Grade an earlier run's recorded trials again, for example after the reference key or a rubric changed."""
        return await self._manager_evaluation.regrade_evaluation(regrade_request, evaluation_artifact_callback)

    def render_scorecard_report(self, scorecard: Scorecard) -> str:
        return self._manager_evaluation.render_scorecard_report(scorecard)
