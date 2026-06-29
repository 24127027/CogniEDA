import os

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from tools import manager as tools_manager


class ModelConfig(BaseModel):
    """Configuration for the OpenAI-compatible chat model used by agents."""

    model_name: str = Field(default_factory=lambda: os.environ.get("COGNIEDA_MODEL_NAME", ""))
    base_url: str = Field(default_factory=lambda: os.environ.get("COGNIEDA_OPENAI_BASE_URL", ""))
    api_key: str = Field(default_factory=lambda: os.environ.get("COGNIEDA_OPENAI_API_KEY", ""))


def create_agent(worker: str, config: ModelConfig) -> Agent:
    if tools_manager.tool_manager is None:
        tools_manager.initialize_tool_manager()

    if tools_manager.tool_manager is None:
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

    return Agent(model=model, toolsets=tools_manager.tool_manager.toolsets_for(worker))