from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Protocol, Literal
from pathlib import Path

from pydantic import BaseModel
from pydantic_ai import Agent

AgentTool = Callable[..., Any]

ProviderType = Literal["openai", "google", "gemini", "anthropic"]
class ModelConfig(BaseModel):
    """Resolved configuration for one OpenAI-compatible model endpoint."""

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
    
# TODO: Consider move this port to somewhere more appropriate, replace or remove it
# This port is still a questionable design choice
# whether the AgentFactory should consume a ToolingConfig 
# or just the paths to the tooling configuration files. 
# These configuration files are not changed at runtime, so it may be simpler to just pass the paths directly.
class ToolingConfig(Protocol):
    @property
    def agents_config_path(self) -> Path: ...

    @property
    def mcp_config_path(self) -> Path: ...

    @property
    def skills_config_path(self) -> Path: ...
