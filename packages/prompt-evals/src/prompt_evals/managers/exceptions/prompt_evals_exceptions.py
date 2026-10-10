from abc import ABC
from typing import Final

type ContextualDataDict = dict[str, str | int | float | bool]


class PromptEvalsExceptionBase(Exception, ABC):
    """Root of the prompt-evals exception taxonomy. Only leaf exceptions are raised."""

    APPLICATION_NAME: Final[str] = "PromptEvals"

    def __init__(self, message: str, contextual_data_by_name: ContextualDataDict) -> None:
        super().__init__(message)
        self._message: str = message
        self._contextual_data_by_name: ContextualDataDict = dict(contextual_data_by_name)

    @property
    def message(self) -> str:
        return self._message

    @property
    def contextual_data_by_name(self) -> ContextualDataDict:
        contextual_data_by_name: ContextualDataDict = {
            "ApplicationName": self.APPLICATION_NAME,
            "ExceptionType": type(self).__name__,
        }
        contextual_data_by_name.update(self._contextual_data_by_name)
        return contextual_data_by_name


class PromptEvalsBusinessExceptionBase(PromptEvalsExceptionBase, ABC):
    """The caller must fix something they supplied: the evaluation request or the eval suite definition."""


class PromptEvalsTechnicalExceptionBase(PromptEvalsExceptionBase, ABC):
    """The environment must be fixed: the coding-assistant CLI, configuration, or the host's artifact storage."""
