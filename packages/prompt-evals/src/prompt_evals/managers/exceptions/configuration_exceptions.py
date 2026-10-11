"""Why a configuration setting cannot be used. Each failure has its own type and one raise site.

A misconfigured environment is always ours to fix, so the whole family is technical.
"""

from abc import ABC
from typing import final

from prompt_evals.managers.exceptions.prompt_evals_exceptions import PromptEvalsTechnicalBaseException


class ConfigurationSettingBaseException(PromptEvalsTechnicalBaseException, ABC):
    def __init__(self, environment_variable_name: str, configured_value: str, expectation: str) -> None:
        super().__init__(
            f"The configuration setting {environment_variable_name}='{configured_value}' is invalid: {expectation}.",
            {"EnvironmentVariableName": environment_variable_name, "ConfiguredValue": configured_value},
        )


@final
class ConfigurationSettingBlankException(ConfigurationSettingBaseException):
    def __init__(self, environment_variable_name: str, configured_value: str) -> None:
        super().__init__(environment_variable_name, configured_value, "expected a non-blank value")


@final
class ConfigurationSettingNotNumberException(ConfigurationSettingBaseException):
    def __init__(self, environment_variable_name: str, configured_value: str) -> None:
        super().__init__(environment_variable_name, configured_value, "expected a number of seconds")


@final
class ConfigurationSettingNumberOutOfRangeException(ConfigurationSettingBaseException):
    def __init__(self, environment_variable_name: str, configured_value: str) -> None:
        super().__init__(environment_variable_name, configured_value, "expected a finite number greater than zero")


@final
class ConfigurationSettingNotWholeNumberException(ConfigurationSettingBaseException):
    def __init__(self, environment_variable_name: str, configured_value: str) -> None:
        super().__init__(environment_variable_name, configured_value, "expected a whole number")


@final
class ConfigurationSettingWholeNumberOutOfRangeException(ConfigurationSettingBaseException):
    def __init__(self, environment_variable_name: str, configured_value: str) -> None:
        super().__init__(environment_variable_name, configured_value, "expected a whole number of at least 1")


@final
class ConfigurationSettingUnknownEffortLevelException(ConfigurationSettingBaseException):
    def __init__(self, environment_variable_name: str, configured_value: str, effort_level_names: str) -> None:
        super().__init__(environment_variable_name, configured_value, f"expected one of {effort_level_names}")


@final
class ConfigurationSettingUnknownCodingAssistantException(ConfigurationSettingBaseException):
    def __init__(self, environment_variable_name: str, configured_value: str, coding_assistant_names: str) -> None:
        super().__init__(environment_variable_name, configured_value, f"expected one of {coding_assistant_names}")
