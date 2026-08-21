from dataclasses import dataclass

from pydantic_ai import Agent

from cognieda.delegation.contracts import ExecutorContext

from .dependencies import DataExplorerDeps


@dataclass
class Context:
    agent: Agent[DataExplorerDeps]
    deps: DataExplorerDeps
    context: ExecutorContext