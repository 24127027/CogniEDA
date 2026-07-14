from collections import defaultdict

from agents.planner.graph import (
    DECISION_ROUTES,
    ENTRY_ROUTES,
    INTENT_ROUTES,
    build_graph,
)
from agents.planner.nodes import registry


def _edges_by_source() -> dict[str, set[str]]:
    graph = build_graph().get_graph()
    edges: dict[str, set[str]] = defaultdict(set)
    for edge in graph.edges:
        edges[edge.source].add(edge.target)
    return edges


def _reachable_nodes() -> set[str]:
    edges = _edges_by_source()
    reachable = {"__start__"}
    pending = ["__start__"]
    while pending:
        for target in edges[pending.pop()]:
            if target not in reachable:
                reachable.add(target)
                pending.append(target)
    return reachable


def test_compiled_graph_contains_every_registered_planner_node() -> None:
    assert set(registry.nodes) <= set(build_graph().get_graph().nodes)


def test_all_declared_router_destinations_are_compiled_nodes() -> None:
    compiled_nodes = set(build_graph().get_graph().nodes)

    assert set(ENTRY_ROUTES.values()) <= compiled_nodes
    assert set(INTENT_ROUTES.values()) <= compiled_nodes
    assert set(DECISION_ROUTES.values()) <= compiled_nodes


def test_every_registered_planner_node_is_reachable_from_start() -> None:
    assert set(registry.nodes) <= _reachable_nodes()


def test_every_registered_planner_node_has_incoming_and_outgoing_edges() -> None:
    edges = _edges_by_source()
    incoming_nodes = {target for targets in edges.values() for target in targets}

    assert set(registry.nodes) <= incoming_nodes
    assert set(registry.nodes) <= set(edges)


def test_connected_workflow_order_includes_execution_processing_chain() -> None:
    edges = _edges_by_source()

    assert "contextual_grounding" in edges["understand_request"]
    assert "prepare_execution" in edges["select_task"]
    assert "request_user_input" in edges["prepare_execution"]
    assert "pause" in edges["request_user_input"]
    assert "process_decision" in edges["pause"]
    assert "commit_execution_contract" in edges["process_decision"]
    assert "dispatch_executor" in edges["commit_execution_contract"]
    assert "review_execution" in edges["dispatch_executor"]
    assert "validate_evidence" in edges["review_execution"]
    assert "evaluate_hypothesis" in edges["validate_evidence"]
    assert "review_conflicts" in edges["evaluate_hypothesis"]
    assert "request_user_input" in edges["review_conflicts"]
    assert "__end__" not in edges["commit_execution_contract"]
    assert "commit" not in edges["review_conflicts"]
