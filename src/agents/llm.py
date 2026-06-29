import os
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic import BaseModel

from tools.manager import tool_manager

class ModelConfig(BaseModel):
    """ 
    Configuration for the custom model.
    """
    model_name: str = "gpt-5.2"
    provider: OpenAIProvider = OpenAIProvider(
        base_url="https://your-custom-endpoint.com/v1",
        api_key=os.environ.get("CUSTOM_API_KEY", "your-api-key"),
    )


def create_agent(worker: str, config: ModelConfig) -> Agent:
    model = OpenAIChatModel(
        model_name=config.model_name,
        provider=config.provider,
    )
    
    return Agent(
        model=model,
        toolsets=tool_manager.toolsets_for(worker),
    )