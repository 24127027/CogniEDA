from unittest.mock import Mock

from cognieda.agents.data_explorer import DataExplorer
from cognieda.agents.graph_miner import GraphMiner
from cognieda.agents.hypothesis_analyst import HypothesisAnalyst
from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.tools import invoke_data_capability
from cognieda.application.ports import ModelConfig
from cognieda.infrastructure.llm import factory as llm_factory


def test_create_agent_forwards_agent_owned_builtin_tools(
    monkeypatch,
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
    monkeypatch.setattr(llm_factory, "OpenAIProvider", provider_factory)
    monkeypatch.setattr(llm_factory, "OpenAIChatModel", model_factory)
    monkeypatch.setattr(llm_factory, "Agent", agent_factory)

    builtin_tools = (invoke_data_capability,)
    deps_type = object

    result = llm_factory.OpenAICompatibleAgentFactory(tooling).create_agent(
        worker="planner",
        config=ModelConfig(model_name="test-model", api_key="test-key"),
        deps_type=deps_type,
        builtin_tools=builtin_tools,
    )

    assert result is agent
    tooling.toolsets_for.assert_called_once_with("planner", builtin_tools)
    tooling.skills_for.assert_called_once_with("planner")
    agent_factory.assert_called_once_with(
        model=model,
        toolsets=[],
        capabilities=[],
        deps_type=deps_type,
    )


def test_concrete_agent_classes_own_their_builtin_tool_selections() -> None:
    assert Planner.builtin_tools == (invoke_data_capability,)
    assert DataExplorer.builtin_tools == ()
    assert GraphMiner.builtin_tools == ()
    assert HypothesisAnalyst.builtin_tools == ()
