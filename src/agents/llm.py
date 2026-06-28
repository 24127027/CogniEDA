import os
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from tools.manager import tool_manager

CUSTOM_MODEL = OpenAIChatModel(
    "gpt-5.2",
    provider=OpenAIProvider(
        base_url="https://your-custom-endpoint.com/v1",
        api_key=os.environ.get("CUSTOM_API_KEY", "your-api-key"),
    ),
)


def create_agent(worker: str) -> Agent:
    return Agent(
        CUSTOM_MODEL, 
        toolsets=tool_manager.toolsets_for(worker),
    )