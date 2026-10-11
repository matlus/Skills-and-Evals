from abc import ABC
from typing import Final, final

from prompt_evals.managers.exceptions.prompt_evals_exceptions import ContextualDataDict, PromptEvalsTechnicalBaseException

DIAGNOSTIC_EXCERPT_MAXIMUM_LENGTH: Final[int] = 2000
MALFORMED_VALUE_EXCERPT_MAXIMUM_LENGTH: Final[int] = 200
EVENT_LINE_CONTEXT_NAME: Final[str] = "EventLineExcerpt"


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
class LlmCliProcessContainmentFailedException(PromptEvalsTechnicalBaseException):
    """The CLI started, but its process could not be contained, so the tool commands it would start could outlive it."""

    def __init__(self, assistant_name: str, model_name: str, containment_failure_description: str) -> None:
        super().__init__(
            f"The {assistant_name} session using model '{model_name}' was stopped because its process could not be contained "
            f"with the processes it starts ({containment_failure_description}).",
            {"AssistantName": assistant_name, "ModelName": model_name, "ContainmentFailure": containment_failure_description},
        )


@final
class LlmCliProcessResumeFailedException(PromptEvalsTechnicalBaseException):
    """The CLI was started suspended so it could be contained before it ran, but it could not be resumed."""

    def __init__(self, assistant_name: str, model_name: str, resume_failure_description: str) -> None:
        super().__init__(
            f"The {assistant_name} session using model '{model_name}' was stopped because its process, started suspended "
            f"so it could be contained before it ran, could not be resumed ({resume_failure_description}).",
            {"AssistantName": assistant_name, "ModelName": model_name, "ResumeFailure": resume_failure_description},
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
    EMPTY_STREAM_TEXT: Final[str] = "(empty)"

    def __init__(self, assistant_name: str, model_name: str, exit_code: int, standard_error_text: str, standard_output_text: str) -> None:
        standard_error_excerpt: str = _bounded_excerpt(standard_error_text)
        standard_output_excerpt: str = _bounded_excerpt(standard_output_text)
        # Claude Code can exit non-zero with stderr empty and the explanation on stdout, so both are kept.
        process_output: str = (
            f"Standard error: {standard_error_excerpt or LlmSessionExitedWithErrorException.EMPTY_STREAM_TEXT} "
            f"Standard output: {standard_output_excerpt or LlmSessionExitedWithErrorException.EMPTY_STREAM_TEXT}"
        )
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


class LlmSessionOutputMalformedBaseException(PromptEvalsTechnicalBaseException, ABC):
    """The CLI's event stream does not have the shape its validator reads. The Claude Code and Codex validators share each
    failure type, so every message names the assistant whose output it is."""

    def __init__(
        self, assistant_name: str, model_name: str, malformation_description: str, malformation_contextual_data_by_name: ContextualDataDict
    ) -> None:
        super().__init__(
            f"The {assistant_name} session using model '{model_name}' produced output that could not be read: {malformation_description}",
            {
                "AssistantName": assistant_name,
                "ModelName": model_name,
                "MalformationDescription": malformation_description,
                **malformation_contextual_data_by_name,
            },
        )


@final
class LlmSessionEventLineNotJsonException(LlmSessionOutputMalformedBaseException):
    def __init__(self, assistant_name: str, model_name: str, event_line: str) -> None:
        event_line_excerpt: str = event_line[:MALFORMED_VALUE_EXCERPT_MAXIMUM_LENGTH]
        super().__init__(assistant_name, model_name, f"a line is not JSON: {event_line_excerpt}", {EVENT_LINE_CONTEXT_NAME: event_line_excerpt})


@final
class LlmSessionEventLineNotJsonObjectException(LlmSessionOutputMalformedBaseException):
    def __init__(self, assistant_name: str, model_name: str, event_line: str) -> None:
        event_line_excerpt: str = event_line[:MALFORMED_VALUE_EXCERPT_MAXIMUM_LENGTH]
        super().__init__(
            assistant_name, model_name, f"a line is not a JSON object: {event_line_excerpt}", {EVENT_LINE_CONTEXT_NAME: event_line_excerpt}
        )


@final
class LlmSessionEventCountUnexpectedException(LlmSessionOutputMalformedBaseException):
    def __init__(self, assistant_name: str, model_name: str, event_description: str, event_count: int) -> None:
        super().__init__(
            assistant_name,
            model_name,
            f"expected exactly one {event_description} event, found {event_count}",
            {"EventDescription": event_description, "EventCount": event_count},
        )


@final
class LlmSessionEventFieldMissingException(LlmSessionOutputMalformedBaseException):
    def __init__(self, assistant_name: str, model_name: str, field_name: str) -> None:
        super().__init__(assistant_name, model_name, f"the field '{field_name}' is missing", {"FieldName": field_name})


@final
class LlmSessionEventFieldTypeInvalidException(LlmSessionOutputMalformedBaseException):
    def __init__(self, assistant_name: str, model_name: str, field_description: str, expected_type_description: str, field_value: object) -> None:
        field_value_excerpt: str = repr(field_value)[:MALFORMED_VALUE_EXCERPT_MAXIMUM_LENGTH]
        super().__init__(
            assistant_name,
            model_name,
            f"{field_description} is {type(field_value).__name__}, not {expected_type_description}: {field_value_excerpt}",
            {"FieldDescription": field_description, "ExpectedType": expected_type_description, "FieldValueExcerpt": field_value_excerpt},
        )


@final
class LlmSessionFailedException(PromptEvalsTechnicalBaseException):
    def __init__(self, assistant_name: str, model_name: str, failure_kind: str, failure_text: str) -> None:
        failure_excerpt: str = _bounded_excerpt(failure_text)
        super().__init__(
            f"The {assistant_name} session using model '{model_name}' ended in error ({failure_kind}): {failure_excerpt}",
            {"AssistantName": assistant_name, "ModelName": model_name, "FailureKind": failure_kind, "FailureExcerpt": failure_excerpt},
        )


# Failures of one session that say nothing about the next one. A CLI that cannot start, or whose process cannot be
# contained or resumed, is deliberately absent: it will fail every session, so it must stop the evaluation instead of
# being recorded per trial. The malformed-output base stands for every way one session's event stream can be unreadable.
SINGLE_SESSION_FAILURE_TYPES: Final[tuple[type[PromptEvalsTechnicalBaseException], ...]] = (
    LlmSessionTimeoutException,
    LlmSessionExitedWithErrorException,
    LlmSessionOutputMalformedBaseException,
    LlmSessionFailedException,
)
