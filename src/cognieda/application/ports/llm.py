from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import BaseModel
from pydantic_ai import Agent

AgentTool = Callable[..., Any]

ProviderType = Literal["openai", "google", "anthropic"]


class ModelConfig(BaseModel):
    """Resolved configuration for one canonical model provider."""

    provider: ProviderType
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

    def reload_tooling(self) -> None: ...


# TODO: Consider moving this port somewhere more appropriate, replacing or removing it.
# This port is still a question of whether AgentFactory should consume ToolingConfig
# or just the paths to the tooling configuration files directly.
class ToolingConfig(Protocol):
    @property
    def agents_config_path(self) -> Path: ...

    @property
    def mcp_config_path(self) -> Path: ...

    @property
    def skills_config_path(self) -> Path: ...
