from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Protocol

from cognieda.agents.planner.agent import Planner
from cognieda.runtime.messages import Message
from cognieda.application.ports import AgentFactoryPort
from cognieda.runtime.workspace import Workspace


@dataclass(frozen=True)
class ParsedCommand:
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class ResolvedCommand:
    name: str
    args: tuple[str, ...]


@dataclass(frozen=True)
class CommandContext:
    workspace: Workspace
    agent_factory: AgentFactoryPort
    planner: Planner

    reload_runtime: Callable[..., Awaitable[None]]
    prompt: Callable[[str], str]
    prompt_secret: Callable[[str], str]


class Command(Protocol):
    name: str
    description: str
    
    async def execute(
        self,
        command: ResolvedCommand,
        context: CommandContext,
    ) -> Message:
        ...