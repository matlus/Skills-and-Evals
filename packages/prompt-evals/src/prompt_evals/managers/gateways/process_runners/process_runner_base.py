from abc import ABC, abstractmethod

from prompt_evals.managers.gateways.process_runners.process_runner_models import ProcessInvocation, ProcessOutcome


class ProcessRunnerBase(ABC):
    """The wire under a coding-assistant CLI gateway: start a process, feed it stdin, collect its output.

    Implementations raise the platform's own errors (FileNotFoundError, TimeoutError, OSError);
    translating them into domain exceptions is the gateway's job.
    """

    @abstractmethod
    async def run_process(self, process_invocation: ProcessInvocation) -> ProcessOutcome: ...
