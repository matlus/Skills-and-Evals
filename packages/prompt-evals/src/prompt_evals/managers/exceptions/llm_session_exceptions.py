from typing import Final, final

from prompt_evals.managers.exceptions.prompt_evals_exceptions import PromptEvalsTechnicalBaseException

DIAGNOSTIC_EXCERPT_MAXIMUM_LENGTH: Final[int] = 2000


def _bounded_excerpt(diagnostic_text: str) -> str:
    stripped_text: str = diagnostic_text.strip()
    if len(stripped_text) <= DIAGNOSTIC_EXCERPT_MAXIMUM_LENGTH:
        return stripped_text
    return stripped_text[-DIAGNOSTIC_EXCERPT_MAXIMUM_LENGTH:]


@final
class LlmCliStartFailedException(PromptEvalsTechnicalBaseException):
    def __init__(self, assistant_name: str, executable_path: str, start_failure_description: str, remedy: str) -> None:
        super().__init__(
            f"The {assistant_name} executable '{executable_path}' could not be started ({start_failure_description}). {remedy}",
            {"AssistantName": assistant_name, "ExecutablePath": executable_path, "StartFailure": start_failure_description},
        )


@final
class LlmSessionTimeoutException(PromptEvalsTechnicalBaseException):
    def __init__(self, assistant_name: str, model_name: str, timeout_seconds: float) -> None:
        super().__init__(
            f"The {assistant_name} session using model '{model_name}' did not finish within {timeout_seconds:g} seconds.",
            {"AssistantName": assistant_name, "ModelName": model_name, "TimeoutSeconds": timeout_seconds},
        )


@final
class LlmSessionExitedWithErrorException(PromptEvalsTechnicalBaseException):
    def __init__(self, assistant_name: str, model_name: str, exit_code: int, standard_error_text: str, standard_output_text: str) -> None:
        standard_error_excerpt: str = _bounded_excerpt(standard_error_text)
        standard_output_excerpt: str = _bounded_excerpt(standard_output_text)
        # Claude Code can exit non-zero with stderr empty and the explanation on stdout, so both are kept.
        process_output: str = f"Standard error: {standard_error_excerpt or '(empty)'} Standard output: {standard_output_excerpt or '(empty)'}"
        super().__init__(
            f"The {assistant_name} session using model '{model_name}' exited with code {exit_code}. {process_output}",
            {
                "AssistantName": assistant_name,
                "ModelName": model_name,
                "ExitCode": exit_code,
                "StandardErrorExcerpt": standard_error_excerpt,
                "StandardOutputExcerpt": standard_output_excerpt,
            },
        )


@final
class LlmSessionOutputMalformedException(PromptEvalsTechnicalBaseException):
    def __init__(self, assistant_name: str, model_name: str, malformation_description: str) -> None:
        super().__init__(
            f"The {assistant_name} session using model '{model_name}' produced output that could not be read: {malformation_description}",
            {"AssistantName": assistant_name, "ModelName": model_name, "MalformationDescription": malformation_description},
        )


@final
class LlmSessionFailedException(PromptEvalsTechnicalBaseException):
    def __init__(self, assistant_name: str, model_name: str, failure_kind: str, failure_text: str) -> None:
        failure_excerpt: str = _bounded_excerpt(failure_text)
        super().__init__(
            f"The {assistant_name} session using model '{model_name}' ended in error ({failure_kind}): {failure_excerpt}",
            {"AssistantName": assistant_name, "ModelName": model_name, "FailureKind": failure_kind, "FailureExcerpt": failure_excerpt},
        )


# Failures of one session that say nothing about the next one. A CLI that cannot start is deliberately absent:
# it will fail every session, so it must stop the evaluation instead of being recorded per trial.
SINGLE_SESSION_FAILURE_TYPES: Final[tuple[type[PromptEvalsTechnicalBaseException], ...]] = (
    LlmSessionTimeoutException,
    LlmSessionExitedWithErrorException,
    LlmSessionOutputMalformedException,
    LlmSessionFailedException,
)
