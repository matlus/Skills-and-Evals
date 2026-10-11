import math
from collections import Counter
from typing import Final, final

from prompt_evals.managers.exceptions.evaluation_request_exceptions import (
    EvaluationRequestValidationException,
    EvaluationRequestVariantsNotInEvalSuiteException,
    RegradeRequestTrialsNotInEvalSuiteException,
    RegradeRequestValidationException,
)
from prompt_evals.managers.models.eval_suite_models import EvalSuite
from prompt_evals.managers.models.evaluation_models import EvaluationRequest
from prompt_evals.managers.models.regrade_models import RegradeRequest
from prompt_evals.managers.models.trial_models import TrialIdentity


@final
class ValidatorEvaluationRequest:
    MODEL_NAME_EMPTY_PROBLEM: Final[str] = "model_name must not be empty"
    TRIAL_LABEL_TEMPLATE: Final[str] = "trial {variant_name} / {case_name} / run {repetition_number}"

    @staticmethod
    def validate(evaluation_request: EvaluationRequest) -> None:
        validation_problems: list[str] = [
            *ValidatorEvaluationRequest._find_repetitions_problems(evaluation_request),
            *ValidatorEvaluationRequest._find_model_name_problems(evaluation_request.model_name),
            *ValidatorEvaluationRequest._find_duplicate_variant_problems(evaluation_request),
        ]
        if validation_problems:
            raise EvaluationRequestValidationException(validation_problems)

    @staticmethod
    def validate_variant_names(evaluation_request: EvaluationRequest, eval_suite: EvalSuite) -> None:
        validation_problems: list[str] = ValidatorEvaluationRequest._find_undefined_requested_variant_problems(evaluation_request, eval_suite)
        if validation_problems:
            raise EvaluationRequestVariantsNotInEvalSuiteException(validation_problems)

    @staticmethod
    def validate_regrade_request(regrade_request: RegradeRequest) -> None:
        validation_problems: list[str] = [
            *ValidatorEvaluationRequest._find_model_name_problems(regrade_request.model_name),
            *ValidatorEvaluationRequest._find_recorded_trials_presence_problems(regrade_request),
            *ValidatorEvaluationRequest._find_duplicate_recorded_trial_problems(regrade_request),
            *ValidatorEvaluationRequest._find_recorded_answer_duration_problems(regrade_request),
        ]
        if validation_problems:
            raise RegradeRequestValidationException(validation_problems)

    @staticmethod
    def validate_recorded_trial_names(regrade_request: RegradeRequest, eval_suite: EvalSuite) -> None:
        # Each undefined name is reported once, however many recorded trials use it.
        validation_problems: list[str] = list(
            dict.fromkeys(
                [
                    *ValidatorEvaluationRequest._find_undefined_recorded_variant_problems(regrade_request, eval_suite),
                    *ValidatorEvaluationRequest._find_undefined_recorded_case_problems(regrade_request, eval_suite),
                ]
            )
        )
        if validation_problems:
            raise RegradeRequestTrialsNotInEvalSuiteException(validation_problems)

    @staticmethod
    def _find_repetitions_problems(evaluation_request: EvaluationRequest) -> list[str]:
        if evaluation_request.repetitions < 1:
            return [f"repetitions must be at least 1 (was {evaluation_request.repetitions})"]
        return []

    @staticmethod
    def _find_model_name_problems(model_name: str) -> list[str]:
        if not model_name.strip():
            return [ValidatorEvaluationRequest.MODEL_NAME_EMPTY_PROBLEM]
        return []

    @staticmethod
    def _find_duplicate_variant_problems(evaluation_request: EvaluationRequest) -> list[str]:
        duplicate_variant_problems: list[str] = []
        variant_name: str
        occurrence_count: int
        for variant_name, occurrence_count in Counter(evaluation_request.variant_names).items():
            if occurrence_count > 1:
                duplicate_variant_problems.append(f"variant '{variant_name}' is requested {occurrence_count} times")
        return duplicate_variant_problems

    @staticmethod
    def _find_recorded_trials_presence_problems(regrade_request: RegradeRequest) -> list[str]:
        if not regrade_request.recorded_trials:
            return ["there are no recorded trials to grade"]
        return []

    @staticmethod
    def _find_duplicate_recorded_trial_problems(regrade_request: RegradeRequest) -> list[str]:
        duplicate_recorded_trial_problems: list[str] = []
        trial_identity: TrialIdentity
        occurrence_count: int
        for trial_identity, occurrence_count in Counter(recorded_trial.trial_identity for recorded_trial in regrade_request.recorded_trials).items():
            if occurrence_count > 1:
                duplicate_recorded_trial_problem: str = (
                    f"{ValidatorEvaluationRequest._describe_trial_label(trial_identity)} is recorded {occurrence_count} times"
                )
                duplicate_recorded_trial_problems.append(duplicate_recorded_trial_problem)
        return duplicate_recorded_trial_problems

    @staticmethod
    def _find_recorded_answer_duration_problems(regrade_request: RegradeRequest) -> list[str]:
        # NaN fails the comparison; infinity and negatives are not durations.
        return [
            ValidatorEvaluationRequest._describe_recorded_answer_duration_problem(
                recorded_trial.trial_identity, recorded_trial.answer_duration_seconds
            )
            for recorded_trial in regrade_request.recorded_trials
            if recorded_trial.answer_duration_seconds is not None and not 0 <= recorded_trial.answer_duration_seconds < math.inf
        ]

    @staticmethod
    def _describe_recorded_answer_duration_problem(trial_identity: TrialIdentity, answer_duration_seconds: float) -> str:
        trial_label: str = ValidatorEvaluationRequest._describe_trial_label(trial_identity)
        return f"{trial_label} has a recorded answer time of {answer_duration_seconds} (expected a finite number of seconds of zero or more)"

    @staticmethod
    def _describe_trial_label(trial_identity: TrialIdentity) -> str:
        return ValidatorEvaluationRequest.TRIAL_LABEL_TEMPLATE.format(
            variant_name=trial_identity.variant_name,
            case_name=trial_identity.case_name,
            repetition_number=trial_identity.repetition_number,
        )

    @staticmethod
    def _find_undefined_requested_variant_problems(evaluation_request: EvaluationRequest, eval_suite: EvalSuite) -> list[str]:
        return [
            f"variant '{variant_name}' is not defined by suite '{eval_suite.eval_suite_name}' "
            f"(defined: {', '.join(ValidatorEvaluationRequest._list_defined_variant_names(eval_suite))})"
            for variant_name in evaluation_request.variant_names
            if not ValidatorEvaluationRequest._is_variant_name_defined(variant_name, eval_suite)
        ]

    @staticmethod
    def _find_undefined_recorded_variant_problems(regrade_request: RegradeRequest, eval_suite: EvalSuite) -> list[str]:
        # A recorded trial can only be graded against a variant the eval suite still defines.
        return [
            f"the recorded variant '{recorded_trial.trial_identity.variant_name}' is not defined by suite '{eval_suite.eval_suite_name}' "
            f"(defined variants: {', '.join(ValidatorEvaluationRequest._list_defined_variant_names(eval_suite))})"
            for recorded_trial in regrade_request.recorded_trials
            if not ValidatorEvaluationRequest._is_variant_name_defined(recorded_trial.trial_identity.variant_name, eval_suite)
        ]

    @staticmethod
    def _find_undefined_recorded_case_problems(regrade_request: RegradeRequest, eval_suite: EvalSuite) -> list[str]:
        # A recorded trial can only be graded against a case the eval suite still defines.
        defined_case_names: list[str] = sorted(eval_case.case_name for eval_case in eval_suite.eval_cases)
        return [
            f"the recorded case '{recorded_trial.trial_identity.case_name}' is not defined by suite '{eval_suite.eval_suite_name}' "
            f"(defined cases: {', '.join(defined_case_names)})"
            for recorded_trial in regrade_request.recorded_trials
            if recorded_trial.trial_identity.case_name not in defined_case_names
        ]

    @staticmethod
    def _is_variant_name_defined(variant_name: str, eval_suite: EvalSuite) -> bool:
        return variant_name in ValidatorEvaluationRequest._list_defined_variant_names(eval_suite)

    @staticmethod
    def _list_defined_variant_names(eval_suite: EvalSuite) -> list[str]:
        return sorted(prompt_variant.variant_name for prompt_variant in eval_suite.prompt_variants)
