from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START
from langgraph.graph.state import CompiledStateGraph, StateGraph

from .nodes import R, registry, route_entry, route_intent, route_process_decision
from .types import Context, State

ENTRY_ROUTES = {
    "understand_request": R.understand_request,
    "resume_execution": R.resume_execution,
}

INTENT_ROUTES = {
    "check_answerability": R.check_answerability,
    "suggest": R.propose_questions,
    "manage_task": R.manage_tasks,
    "execute": R.select_task,
    "objective": R.manage_objective,
    "assumption": R.manage_assumptions,
    "invalid_request": R.invalid_request,
    # Preserve the current temporary behavior for recognized but unsupported commands.
    "register_dataset": R.invalid_request,
    "close_project": R.invalid_request,
    "profile": R.invalid_request,
    "review_profile": R.invalid_request,
    "clean": R.invalid_request,
    "accept_profile": R.invalid_request,
    "review_result": R.review_result,
    "review_conflict": R.review_conflict,
}

DECISION_ROUTES = {
    "clarify": R.understand_request,
    "approved_questions": R.expand_plan,
    "approved_task": R.commit,
    "approved_plan": R.commit,
    "approved_conflict": R.commit,
    "approved_execution": R.commit_execution_contract,
    "cancel": R.commit,
}


def build_graph(
    *, checkpointer: BaseCheckpointSaver[Any] | None = None
) -> CompiledStateGraph[State, Context, State, State]:
    builder = StateGraph(State, context_schema=Context)

    # --------------------------------------------------
    # Register all nodes
    # --------------------------------------------------

    for name, func in registry.nodes.items():
        builder.add_node(name, func)

    # --------------------------------------------------
    # Entry
    # --------------------------------------------------

    builder.add_conditional_edges(
        START,
        route_entry,
        ENTRY_ROUTES,
    )

    # --------------------------------------------------
    # Intent routing
    # --------------------------------------------------

    builder.add_conditional_edges(
        R.understand_request,
        route_intent,
        {
            "invalid_request": R.invalid_request,
            **{k: R.contextual_grounding for k in INTENT_ROUTES if k != "invalid_request"},
        },
    )

    builder.add_conditional_edges(
        R.contextual_grounding,
        route_intent,
        INTENT_ROUTES,
    )

    # --------------------------------------------------
    # Question answering
    # --------------------------------------------------

    builder.add_edge(R.check_answerability, R.answer_question)
    builder.add_edge(R.answer_question, R.commit)

    # --------------------------------------------------
    # Research planning
    # --------------------------------------------------

    builder.add_edge(R.propose_questions, R.request_user_input)
    builder.add_edge(R.expand_plan, R.request_user_input)
    # --------------------------------------------------
    # Task management
    # --------------------------------------------------

    builder.add_edge(R.manage_tasks, R.request_user_input)

    # --------------------------------------------------
    # Execution
    # --------------------------------------------------

    builder.add_edge(R.select_task, R.prepare_execution)
    # Execution is deliberately approval-gated.  A prepared contract is not a
    # dispatch authorization until the decision node revalidates its snapshot.
    builder.add_edge(R.prepare_execution, R.request_user_input)
    builder.add_edge(R.commit_execution_contract, END)

    # --------------------------------------------------
    # Knowledge management
    # --------------------------------------------------

    builder.add_edge(R.manage_objective, R.request_user_input)
    builder.add_edge(R.manage_assumptions, R.request_user_input)

    # --------------------------------------------------
    # User interaction
    # --------------------------------------------------

    builder.add_edge(R.request_user_input, R.pause)
    builder.add_edge(R.pause, R.process_decision)
    builder.add_edge(R.resume_execution, R.process_decision)

    builder.add_conditional_edges(
        R.process_decision,
        route_process_decision,
        DECISION_ROUTES,
    )

    # --------------------------------------------------
    # Finish
    # --------------------------------------------------

    builder.add_edge(R.invalid_request, END)
    builder.add_edge(R.commit, END)

    interrupt_before = ["pause"] if checkpointer is not None else None
    return builder.compile(checkpointer=checkpointer, interrupt_before=interrupt_before)


if __name__ == "__main__":
    agent_graph = build_graph()
    agent_graph.get_graph().draw_mermaid_png(output_file_path="graph.png")
