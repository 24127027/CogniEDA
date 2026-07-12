import pytest
from pydantic_ai import FunctionToolset

from tools.builtin_tools import AvailableBuiltinTools
from tools.manager import ToolManager


def test_explicit_builtin_tools_are_wrapped_in_one_function_toolset() -> None:
    manager = ToolManager(config={"test_worker": {}}, mcp_toolsets={}, skills={})

    toolsets = manager.toolsets_for(
        "test_worker",
        (AvailableBuiltinTools.GRAPH, AvailableBuiltinTools.DATASET),
    )

    assert len(toolsets) == 1
    function_toolset = toolsets[0]
    assert isinstance(function_toolset, FunctionToolset)
    assert set(function_toolset.tools) == {
        "create_graph_toolset",
        "create_dataset_toolset",
    }


def test_worker_without_builtin_tools_has_no_function_toolset() -> None:
    manager = ToolManager(config={"planner": {}}, mcp_toolsets={}, skills={})

    toolsets = manager.toolsets_for("planner", ())

    assert toolsets == []


def test_unknown_worker_is_rejected() -> None:
    manager = ToolManager(config={}, mcp_toolsets={}, skills={})

    with pytest.raises(ValueError, match="Unknown worker 'missing_worker'"):
        manager.toolsets_for("missing_worker", ())
