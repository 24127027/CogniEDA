import os

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from tools.manager import initialize_tool_manager, tool_manager

class ModelConfig(BaseModel):
    """Configuration for the OpenAI-compatible chat model used by agents."""

    model_name: str = Field(default_factory=lambda: os.environ.get("COGNIEDA_MODEL_NAME", ""))
    base_url: str = Field(default_factory=lambda: os.environ.get("COGNIEDA_OPENAI_BASE_URL", ""))
    api_key: str = Field(default_factory=lambda: os.environ.get("COGNIEDA_OPENAI_API_KEY", ""))


def create_agent(worker: str, config: ModelConfig) -> Agent:
    # TODO: should move initialization of tool manager to bootstrap
    if tool_manager is None:
        initialize_tool_manager()

    if tool_manager is None:
        raise RuntimeError("Tool manager was not initialized.")

    if not config.model_name:
        raise ValueError("COGNIEDA_MODEL_NAME must be set to create an agent.")

    if not config.api_key:
        raise ValueError("COGNIEDA_OPENAI_API_KEY must be set to create an agent.")

    provider = OpenAIProvider(
        api_key=config.api_key,
        base_url=config.base_url if config.base_url else None
    )    
    model = OpenAIChatModel(model_name=config.model_name, provider=provider)

    # Get toolsets (MCP and builtin tools)
    toolsets = tool_manager.toolsets_for(worker)
    
    # Get skills (high-level capabilities)
    skills = tool_manager.skills_for(worker)
    
    # Create agent with both toolsets and skills
    agent = Agent(model=model, toolsets=toolsets, capabilities=skills)

    return agent