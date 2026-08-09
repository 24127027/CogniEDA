from collections.abc import Sequence

from pydantic_ai import Agent

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider

from cognieda.application.ports import AgentTool, ModelConfig
from cognieda.infrastructure.agent_tooling import AgentTooling

class AgentFactory:
    """Construct PydanticAI agents from explicitly injected external tooling."""

    def __init__(self, tooling: AgentTooling) -> None:
        self._tooling = tooling

    def create_agent[DepsT](
        self,
        *,
        worker: str,
        config: ModelConfig,
        deps_type: type[DepsT],
        builtin_tools: Sequence[AgentTool],
    ) -> Agent[DepsT]:

        if not config.model_name:
            raise ValueError("model_name must be configured to create an agent.")

        if not config.api_key:
            raise ValueError("api_key must be configured to create an agent.")

        model = _choose_model(config)

        toolsets = self._tooling.toolsets_for(worker, builtin_tools)
        skills = self._tooling.skills_for(worker)

        return Agent(
            model=model,
            toolsets=toolsets,
            capabilities=skills,
            deps_type=deps_type,
        )

def _choose_model(config: ModelConfig):
    if config.provider == "openai":
        provider = OpenAIProvider(
            api_key=config.api_key,
            base_url=config.base_url if config.base_url else None,
        )
        return OpenAIChatModel(model_name=config.model_name, provider=provider)
    elif config.provider == "google" or config.provider == "gemini":
        provider = GoogleProvider(
            api_key=config.api_key,
            base_url=config.base_url if config.base_url else None,
        )
        return GoogleModel(model_name=config.model_name, provider=provider)
    elif config.provider == "anthropic":
        provider = AnthropicProvider(
            api_key=config.api_key,
            base_url=config.base_url if config.base_url else None,
        )
        return AnthropicModel(model_name=config.model_name, provider=provider)

    else:
        raise ValueError(f"Unsupported model provider: {config.provider}")