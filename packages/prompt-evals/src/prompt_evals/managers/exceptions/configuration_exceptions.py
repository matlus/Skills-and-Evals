from typing import final

from prompt_evals.managers.exceptions.prompt_evals_exceptions import PromptEvalsTechnicalExceptionBase


@final
class ConfigurationSettingException(PromptEvalsTechnicalExceptionBase):
    def __init__(self, environment_variable_name: str, configured_value: str, expectation: str) -> None:
        super().__init__(
            f"The configuration setting {environment_variable_name}='{configured_value}' is invalid: {expectation}.",
            {"EnvironmentVariableName": environment_variable_name, "ConfiguredValue": configured_value},
        )
