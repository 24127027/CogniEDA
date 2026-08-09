from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Protocol

from pydantic import BaseModel
from pydantic_ai import Agent

AgentTool = Callable[..., Any]


class ModelConfig(BaseModel):
    """Resolved configuration for one OpenAI-compatible model endpoint."""

    model_name: str = ""
    base_url: str = ""
    api_key: str = ""


class AgentFactoryPort(Protocol):
    def create_agent[DepsT](
        self,
        *,
        worker: str,
        config: ModelConfig,
        deps_type: type[DepsT],
        builtin_tools: Sequence[AgentTool],
    ) -> Agent[DepsT]: ...
