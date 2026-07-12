from unittest.mock import Mock

from agents import llm
from agents.executor.graph_miner.agent import GraphMiner
from agents.executor.hypothesis_analyst.agent import HypothesisAnalyst
from agents.planner.agent import Planner
from tools.builtin_tools import AvailableBuiltinTools


def test_create_agent_forwards_agent_owned_builtin_tools(
    monkeypatch,
) -> None:
    manager = Mock()
    manager.toolsets_for.return_value = []
    manager.skills_for.return_value = []
    monkeypatch.setattr(llm, "tool_manager", manager)

    provider = object()
    model = object()
    agent = object()
    provider_factory = Mock(return_value=provider)
    model_factory = Mock(return_value=model)
    agent_factory = Mock(return_value=agent)
    monkeypatch.setattr(llm, "OpenAIProvider", provider_factory)
    monkeypatch.setattr(llm, "OpenAIChatModel", model_factory)
    monkeypatch.setattr(llm, "Agent", agent_factory)

    builtin_tools = (AvailableBuiltinTools.GRAPH,)
    deps_type = object

    result = llm.create_agent(
        worker="planner",
        config=llm.ModelConfig(model_name="test-model", api_key="test-key"),
        deps_type=deps_type,
        builtin_tools=builtin_tools,
    )

    assert result is agent
    manager.toolsets_for.assert_called_once_with("planner", builtin_tools)
    manager.skills_for.assert_called_once_with("planner")
    agent_factory.assert_called_once_with(
        model=model,
        toolsets=[],
        capabilities=[],
        deps_type=deps_type,
    )


def test_concrete_agent_classes_own_their_builtin_tool_selections() -> None:
    assert Planner.builtin_tools == (AvailableBuiltinTools.GRAPH,)
    assert GraphMiner.builtin_tools == (AvailableBuiltinTools.GRAPH,)
    assert HypothesisAnalyst.builtin_tools == (AvailableBuiltinTools.DATASET,)
