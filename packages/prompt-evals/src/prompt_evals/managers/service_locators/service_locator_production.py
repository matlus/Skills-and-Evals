from typing import final, override

from prompt_evals.managers.configuration_providers.configuration_provider import ConfigurationProvider
from prompt_evals.managers.configuration_providers.setting_sources.environment_setting_source import EnvironmentSettingSource
from prompt_evals.managers.gateways.process_runners.process_runner_asyncio import ProcessRunnerAsyncio
from prompt_evals.managers.gateways.process_runners.process_runner_base import ProcessRunnerBase
from prompt_evals.managers.service_locators.service_locator_base import ServiceLocatorBase


@final
class ServiceLocatorProduction(ServiceLocatorBase):
    @override
    def get_configuration_provider(self) -> ConfigurationProvider:
        return ConfigurationProvider(EnvironmentSettingSource())

    @override
    def create_process_runner(self) -> ProcessRunnerBase:
        return ProcessRunnerAsyncio()
