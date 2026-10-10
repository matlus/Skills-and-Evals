import math
from typing import Final, final

from prompt_evals.managers.configuration_providers.setting_sources.setting_source_protocol import SettingSourceProtocol
from prompt_evals.managers.configuration_providers.settings_models.claude_cli_settings import ClaudeCliSettings
from prompt_evals.managers.configuration_providers.settings_models.codex_cli_settings import CodexCliSettings
from prompt_evals.managers.configuration_providers.settings_models.grading_settings import GradingSettings
from prompt_evals.managers.configuration_providers.settings_models.trial_execution_settings import TrialExecutionSettings
from prompt_evals.managers.exceptions.configuration_exceptions import ConfigurationSettingException
from prompt_evals.managers.models.evaluation_models import CodingAssistant, EffortLevel

CLAUDE_EXECUTABLE_VARIABLE: Final[str] = "PROMPT_EVALS_CLAUDE_EXECUTABLE"
CODEX_EXECUTABLE_VARIABLE: Final[str] = "PROMPT_EVALS_CODEX_EXECUTABLE"
SESSION_TIMEOUT_SECONDS_VARIABLE: Final[str] = "PROMPT_EVALS_SESSION_TIMEOUT_SECONDS"
MAXIMUM_CONCURRENT_TRIALS_VARIABLE: Final[str] = "PROMPT_EVALS_MAXIMUM_CONCURRENT_TRIALS"
GRADER_ASSISTANT_VARIABLE: Final[str] = "PROMPT_EVALS_GRADER_ASSISTANT"
GRADER_MODEL_VARIABLE: Final[str] = "PROMPT_EVALS_GRADER_MODEL"
GRADER_EFFORT_VARIABLE: Final[str] = "PROMPT_EVALS_GRADER_EFFORT"
MAXIMUM_CONCURRENT_GRADINGS_VARIABLE: Final[str] = "PROMPT_EVALS_MAXIMUM_CONCURRENT_GRADINGS"

DEFAULT_CLAUDE_EXECUTABLE: Final[str] = "claude"
DEFAULT_CODEX_EXECUTABLE: Final[str] = "codex"
DEFAULT_SESSION_TIMEOUT_SECONDS: Final[str] = "900"
DEFAULT_MAXIMUM_CONCURRENT_TRIALS: Final[str] = "2"
DEFAULT_GRADER_ASSISTANT: Final[str] = CodingAssistant.CLAUDE_CODE.value
DEFAULT_GRADER_MODEL: Final[str] = "sonnet"
DEFAULT_GRADER_EFFORT: Final[str] = EffortLevel.LOW.value
DEFAULT_MAXIMUM_CONCURRENT_GRADINGS: Final[str] = "3"


@final
class ConfigurationProvider:
    """Builds the settings each component needs from the setting source's values, falling back to defaults."""

    def __init__(self, setting_source: SettingSourceProtocol) -> None:
        self._setting_source: SettingSourceProtocol = setting_source

    def get_claude_cli_settings(self) -> ClaudeCliSettings:
        return ClaudeCliSettings(
            executable_path=self._read_setting(CLAUDE_EXECUTABLE_VARIABLE, DEFAULT_CLAUDE_EXECUTABLE),
            session_timeout_seconds=self._read_positive_number(SESSION_TIMEOUT_SECONDS_VARIABLE, DEFAULT_SESSION_TIMEOUT_SECONDS),
        )

    def get_codex_cli_settings(self) -> CodexCliSettings:
        return CodexCliSettings(
            executable_path=self._read_setting(CODEX_EXECUTABLE_VARIABLE, DEFAULT_CODEX_EXECUTABLE),
            session_timeout_seconds=self._read_positive_number(SESSION_TIMEOUT_SECONDS_VARIABLE, DEFAULT_SESSION_TIMEOUT_SECONDS),
        )

    def get_trial_execution_settings(self) -> TrialExecutionSettings:
        return TrialExecutionSettings(
            maximum_concurrent_trials=self._read_positive_integer(MAXIMUM_CONCURRENT_TRIALS_VARIABLE, DEFAULT_MAXIMUM_CONCURRENT_TRIALS),
        )

    def get_grading_settings(self) -> GradingSettings:
        return GradingSettings(
            grader_coding_assistant=self._read_coding_assistant(GRADER_ASSISTANT_VARIABLE, DEFAULT_GRADER_ASSISTANT),
            grader_model_name=self._read_setting(GRADER_MODEL_VARIABLE, DEFAULT_GRADER_MODEL),
            grader_effort_level=self._read_effort_level(GRADER_EFFORT_VARIABLE, DEFAULT_GRADER_EFFORT),
            maximum_concurrent_gradings=self._read_positive_integer(MAXIMUM_CONCURRENT_GRADINGS_VARIABLE, DEFAULT_MAXIMUM_CONCURRENT_GRADINGS),
        )

    def _read_setting(self, environment_variable_name: str, default_value: str) -> str:
        configured_value: str | None = self._setting_source.read_setting_value(environment_variable_name)
        if configured_value is None:
            return default_value
        # A variable set to nothing is a mistake to report now, not a value to fail on after every paid trial has run.
        if not configured_value.strip():
            raise ConfigurationSettingException(environment_variable_name, configured_value, "expected a non-blank value")
        return configured_value

    def _read_positive_number(self, environment_variable_name: str, default_value: str) -> float:
        configured_value: str = self._read_setting(environment_variable_name, default_value)
        try:
            configured_number: float = float(configured_value)
        except ValueError as value_error:
            raise ConfigurationSettingException(environment_variable_name, configured_value, "expected a number of seconds") from value_error
        if not math.isfinite(configured_number) or configured_number <= 0:
            raise ConfigurationSettingException(environment_variable_name, configured_value, "expected a finite number greater than zero")
        return configured_number

    def _read_positive_integer(self, environment_variable_name: str, default_value: str) -> int:
        configured_value: str = self._read_setting(environment_variable_name, default_value)
        try:
            configured_integer: int = int(configured_value)
        except ValueError as value_error:
            raise ConfigurationSettingException(environment_variable_name, configured_value, "expected a whole number") from value_error
        if configured_integer < 1:
            raise ConfigurationSettingException(environment_variable_name, configured_value, "expected a whole number of at least 1")
        return configured_integer

    def _read_effort_level(self, environment_variable_name: str, default_value: str) -> EffortLevel:
        configured_value: str = self._read_setting(environment_variable_name, default_value)
        try:
            return EffortLevel(configured_value)
        except ValueError as value_error:
            effort_level_names: str = ", ".join(effort_level.value for effort_level in EffortLevel)
            raise ConfigurationSettingException(environment_variable_name, configured_value, f"expected one of {effort_level_names}") from value_error

    def _read_coding_assistant(self, environment_variable_name: str, default_value: str) -> CodingAssistant:
        configured_value: str = self._read_setting(environment_variable_name, default_value)
        try:
            return CodingAssistant(configured_value)
        except ValueError as value_error:
            coding_assistant_names: str = ", ".join(coding_assistant.value for coding_assistant in CodingAssistant)
            raise ConfigurationSettingException(
                environment_variable_name, configured_value, f"expected one of {coding_assistant_names}"
            ) from value_error
