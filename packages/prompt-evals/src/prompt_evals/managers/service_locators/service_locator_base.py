from abc import ABC, abstractmethod

from prompt_evals.managers.configuration_providers.configuration_provider import ConfigurationProvider
from prompt_evals.managers.gateways.gateway_claude_cli import GatewayLlmClaudeCli
from prompt_evals.managers.gateways.gateway_codex_cli import GatewayLlmCodexCli
from prompt_evals.managers.gateways.gateway_llm_protocol import GatewayLlmProtocol
from prompt_evals.managers.gateways.process_runners.process_runner_base import ProcessRunnerBase
from prompt_evals.managers.models.evaluation_models import CodingAssistant


class ServiceLocatorBase(ABC):
    """Creates only what tests must swap. Tests supply a process-runner spy so the real
    coding-assistant gateway (command composition, output parsing, error translation) runs in every test."""

    @abstractmethod
    def get_configuration_provider(self) -> ConfigurationProvider: ...

    @abstractmethod
    def create_process_runner(self) -> ProcessRunnerBase: ...

    def create_gateway_llm(self, coding_assistant: CodingAssistant) -> GatewayLlmProtocol:
        """The one place that knows which gateway serves each coding assistant."""
        match coding_assistant:
            case CodingAssistant.CLAUDE_CODE:
                return GatewayLlmClaudeCli(self.get_configuration_provider().get_claude_cli_settings(), self.create_process_runner())
            case CodingAssistant.CODEX:
                return GatewayLlmCodexCli(self.get_configuration_provider().get_codex_cli_settings(), self.create_process_runner())
