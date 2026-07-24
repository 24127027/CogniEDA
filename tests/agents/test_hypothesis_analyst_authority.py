"""Import, dependency, tool, and framework-boundary tests for Hypothesis Analyst."""

from __future__ import annotations

import ast
import inspect

from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from agents.executor.hypothesis_analyst import agent as analyst_facade
from agents.executor.hypothesis_analyst import nodes as analyst_nodes
from agents.executor.hypothesis_analyst.nodes import (
    HypothesisAnalystDependencies,
    build_hypothesis_analyst_agent,
)
from agents.executor.hypothesis_analyst.state import State
from tools.builtin_tools import AvailableBuiltinTools

FORBIDDEN_IMPORT_FRAGMENTS = (
    "repositories",
    "db",
    "sqlalchemy",
    "sqlmodel",
    "filesystem",
    "dataset",
    "session_frame",
    "planner",
    "data_explorer",
    "scientific_processing",
    "commit",
)


def _import_names(module: object) -> set[str]:
    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
    return names


def test_active_analyst_has_no_forbidden_import_or_generic_dependency_surface() -> None:
    imports = _import_names(analyst_nodes)
    assert not {
        name
        for name in imports
        if any(fragment in name.lower() for fragment in FORBIDDEN_IMPORT_FRAGMENTS)
    }
    assert set(HypothesisAnalystDependencies.__dataclass_fields__) == {"bundle"}
    assert State.__annotations__ == {}


def test_real_pydantic_ai_agent_has_typed_output_bounded_retries_and_zero_tools() -> None:
    agent = build_hypothesis_analyst_agent(model=TestModel())

    assert isinstance(agent, Agent)
    assert agent._function_toolset.tools == {}
    assert agent._user_toolsets == []
    assert agent._dynamic_toolsets == []
    assert agent._cap_toolsets == []
    assert analyst_facade.HypothesisAnalyst.builtin_tools == ()
    assert AvailableBuiltinTools.DATASET not in analyst_facade.HypothesisAnalyst.builtin_tools
    assert "HypothesisAnalystResult" in repr(agent)


def test_hypothesis_analyst_is_not_registered_as_generic_data_executor() -> None:
    import agents.executor.registry as registry_module

    assert not hasattr(registry_module, "executor_registry")
