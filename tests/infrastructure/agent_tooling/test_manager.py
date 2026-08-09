import pytest
from pydantic_ai import FunctionToolset

from cognieda.infrastructure.agent_tooling import AgentTooling


def first_tool() -> None:
    return None


def second_tool() -> None:
    return None


def test_explicit_builtin_tools_are_wrapped_in_one_function_toolset() -> None:
    manager = AgentTooling(config={"test_worker": {}}, mcp_toolsets={}, skills={})

    toolsets = manager.toolsets_for(
        "test_worker",
        (first_tool, second_tool),
    )

    assert len(toolsets) == 1
    function_toolset = toolsets[0]
    assert isinstance(function_toolset, FunctionToolset)
    assert set(function_toolset.tools) == {
        "first_tool",
        "second_tool",
    }


def test_worker_without_builtin_tools_has_no_function_toolset() -> None:
    manager = AgentTooling(config={"planner": {}}, mcp_toolsets={}, skills={})

    toolsets = manager.toolsets_for("planner", ())

    assert toolsets == []


def test_unknown_worker_is_rejected() -> None:
    manager = AgentTooling(config={}, mcp_toolsets={}, skills={})

    with pytest.raises(ValueError, match="Unknown worker 'missing_worker'"):
        manager.toolsets_for("missing_worker", ())


def test_missing_development_config_uses_bounded_planner_defaults(tmp_path) -> None:
    manager = AgentTooling.from_config_path(
        path=tmp_path / "missing-agents.toml",
        mcp_path=tmp_path / "missing-mcp.toml",
        skills_path=tmp_path / "missing-skills.toml",
    )

    assert manager.toolsets_for("planner", ()) == []
    assert manager.skills_for("planner") == []
    assert manager.toolsets_for("data_explorer", ()) == []
