from collections.abc import Mapping
from typing import override

from acceptance_support.process_runner_spy import ProcessRunnerSpy
from acceptance_support.setting_source_stub import SettingSourceStub
from acceptance_support.test_mediator_coding_assistant_cli import TestMediatorCodingAssistantCli
from prompt_evals import DomainFacade
from prompt_evals.managers.configuration_providers.configuration_provider import ConfigurationProvider
from prompt_evals.managers.gateways.process_runners.process_runner_base import ProcessRunnerBase
from prompt_evals.managers.service_locators.service_locator_base import ServiceLocatorBase


class ServiceLocatorTesting(ServiceLocatorBase):
    def __init__(
        self, test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli, override_by_environment_variable_name: Mapping[str, str]
    ) -> None:
        self._test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = test_mediator_coding_assistant_cli
        self._override_by_environment_variable_name: Mapping[str, str] = override_by_environment_variable_name

    @override
    def get_configuration_provider(self) -> ConfigurationProvider:
        return ConfigurationProvider(SettingSourceStub(self._override_by_environment_variable_name))

    @override
    def create_process_runner(self) -> ProcessRunnerBase:
        return ProcessRunnerSpy(self._test_mediator_coding_assistant_cli)


def create_domain_facade(
    test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli, override_by_environment_variable_name: Mapping[str, str]
) -> DomainFacade:
    return DomainFacade(ServiceLocatorTesting(test_mediator_coding_assistant_cli, override_by_environment_variable_name))
