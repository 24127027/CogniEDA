from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Protocol

from cognieda.agents.planner.agent import Planner
from cognieda.application.ports import AgentFactoryPort
from cognieda.runtime.messages import Message
from cognieda.runtime.workspace import Workspace


@dataclass(frozen=True)
class ParsedCommand:
    name: str
    args: tuple[str, ...]


@dataclass(frozen=True)
class CommandContext:
    workspace: Workspace
    agent_factory: AgentFactoryPort
    planner: Planner

    reload_runtime: Callable[..., Awaitable[None]]
    prompt_secret: Callable[[str], str]


class Command(Protocol):
    name: str

    async def execute(
        self,
        command: ParsedCommand,
        context: CommandContext,
    ) -> Message:
        ...