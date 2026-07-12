import os
from collections.abc import Sequence

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from tools.builtin_tools import AvailableBuiltinTools
from tools.manager import initialize_tool_manager, tool_manager


class ModelConfig(BaseModel):
    """Configuration for the OpenAI-compatible chat model used by agents."""

    model_name: str = Field(default_factory=lambda: os.environ.get("COGNIEDA_MODEL_NAME", ""))
    base_url: str = Field(default_factory=lambda: os.environ.get("COGNIEDA_OPENAI_BASE_URL", ""))
    api_key: str = Field(default_factory=lambda: os.environ.get("COGNIEDA_OPENAI_API_KEY", ""))


def create_agent[DepsT](
    worker: str,
    config: ModelConfig,
    deps_type: type[DepsT],
    builtin_tools: Sequence[AvailableBuiltinTools],
) -> Agent[DepsT]:
    # TODO: should move initialization of tool manager to bootstrap
    manager = tool_manager
    if manager is None:
        manager = initialize_tool_manager()

    if not config.model_name:
        raise ValueError("COGNIEDA_MODEL_NAME must be set to create an agent.")

    if not config.api_key:
        raise ValueError("COGNIEDA_OPENAI_API_KEY must be set to create an agent.")

    provider = OpenAIProvider(
        api_key=config.api_key,
        base_url=config.base_url if config.base_url else None,
    )
    model = OpenAIChatModel(model_name=config.model_name, provider=provider)

    # Get toolsets (MCP and builtin tools)
    toolsets = manager.toolsets_for(worker, builtin_tools)

    # Get skills (high-level capabilities)
    skills = manager.skills_for(worker)

    # Create agent with both toolsets and skills
    agent = Agent(
        model=model,
        toolsets=toolsets,
        capabilities=skills,
        deps_type=deps_type,
    )

    return agent
