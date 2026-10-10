from typing import override

from acceptance_support.test_mediator_coding_assistant_cli import TestMediatorCodingAssistantCli
from prompt_evals.managers.gateways.process_runners.process_runner_base import ProcessRunnerBase
from prompt_evals.managers.gateways.process_runners.process_runner_models import ProcessInvocation, ProcessOutcome


class ProcessRunnerSpy(ProcessRunnerBase):
    """Replaces only the wire: no process starts. Everything above it, including the real gateway, still runs."""

    def __init__(self, test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli) -> None:
        self._test_mediator_coding_assistant_cli: TestMediatorCodingAssistantCli = test_mediator_coding_assistant_cli

    @override
    async def run_process(self, process_invocation: ProcessInvocation) -> ProcessOutcome:
        return self._test_mediator_coding_assistant_cli.respond_to_invocation(process_invocation)
