from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Protocol, Literal

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
