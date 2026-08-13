from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from cognieda.agents.data_explorer import DataExplorer
from cognieda.agents.graph_miner import GraphMiner
from cognieda.agents.hypothesis_analyst import HypothesisAnalyst
from cognieda.agents.planner.agent import Planner
from cognieda.application.ports import ModelConfig
from cognieda.infrastructure.llm import factory as llm_factory


def _builtin_tool() -> str:
    return "tool result"


@pytest.mark.parametrize(
    ("provider_name", "provider_attribute", "model_attribute"),
    [
        ("openai", "OpenAIProvider", "OpenAIChatModel"),
        ("google", "GoogleProvider", "GoogleModel"),
        ("anthropic", "AnthropicProvider", "AnthropicModel"),
    ],
)
def test_create_agent_selects_canonical_provider_and_forwards_builtin_tools(
    monkeypatch,
    provider_name: str,
    provider_attribute: str,
    model_attribute: str,
) -> None:
    tooling = Mock()
    tooling.toolsets_for.return_value = []
    tooling.skills_for.return_value = []

    provider = object()
    model = object()
    agent = object()
    provider_factory = Mock(return_value=provider)
    model_factory = Mock(return_value=model)
    agent_factory = Mock(return_value=agent)
    monkeypatch.setattr(llm_factory, provider_attribute, provider_factory)
    monkeypatch.setattr(llm_factory, model_attribute, model_factory)
    monkeypatch.setattr(llm_factory, "Agent", agent_factory)

    builtin_tools = (_builtin_tool,)
    deps_type = object

    result = llm_factory.AgentFactory(tooling).create_agent(
        worker="planner",
        config=ModelConfig(
            provider=provider_name,
            model_name="test-model",
            base_url="https://models.example/v1",
            api_key="test-key",
        ),
        deps_type=deps_type,
        builtin_tools=builtin_tools,
    )

    assert result is agent
    provider_factory.assert_called_once_with(
        api_key="test-key",
        base_url="https://models.example/v1",
    )
    model_factory.assert_called_once_with(model_name="test-model", provider=provider)
    tooling.toolsets_for.assert_called_once_with("planner", builtin_tools)
    tooling.skills_for.assert_called_once_with("planner")
    agent_factory.assert_called_once_with(
        model=model,
        toolsets=[],
        capabilities=[],
        deps_type=deps_type,
    )


@pytest.mark.parametrize(
    ("model_name", "api_key", "message"),
    [
        ("", "test-key", "model_name must be configured"),
        ("test-model", "", "api_key must be configured"),
    ],
)
def test_create_agent_rejects_missing_required_configuration(
    model_name: str,
    api_key: str,
    message: str,
) -> None:
    tooling = Mock()

    with pytest.raises(ValueError, match=message):
        llm_factory.AgentFactory(tooling).create_agent(
            worker="planner",
            config=ModelConfig(
                provider="openai",
                model_name=model_name,
                api_key=api_key,
            ),
            deps_type=object,
            builtin_tools=(),
        )


def test_model_config_rejects_gemini_after_the_input_boundary() -> None:
    with pytest.raises(ValidationError, match="openai.*google.*anthropic"):
        ModelConfig(
            provider="gemini",
            model_name="test-model",
            api_key="test-key",
        )


def test_data_explorer_requires_model_config_only_for_model_backed_planning() -> None:
    assert DataExplorer().config is None

    with pytest.raises(ValueError, match="Model configuration is required"):
        DataExplorer(agent_factory=Mock())


def test_concrete_agent_classes_own_their_builtin_tool_selections() -> None:
    assert Planner.builtin_tools == ()
    assert DataExplorer.builtin_tools == ()
    assert GraphMiner.builtin_tools == ()
    assert HypothesisAnalyst.builtin_tools == ()
