from langgraph.graph.state import StateGraph, CompiledStateGraph
from langgraph.graph import START, END

from .types import PlannerState
from .nodes import registry, R


def build_graph() -> CompiledStateGraph:
    builder = StateGraph(PlannerState)

    # --------------------------------------------------
    # Register all nodes
    # --------------------------------------------------

    for name, func in registry.nodes.items():
        builder.add_node(name, func)

    # --------------------------------------------------
    # Entry
    # --------------------------------------------------

    builder.add_edge(START, R.understand_request)
    builder.add_edge(R.understand_request, R.route_intent)

    # --------------------------------------------------
    # Intent routing
    # --------------------------------------------------

    builder.add_conditional_edges(
        R.route_intent,
        registry.nodes[R.route_intent],
        {
            "answer": R.answer_question,
            "suggest": R.propose_questions,
            "manage_task": R.manage_tasks,
            "execute": R.select_task,
            "objective": R.manage_objective,
            "assumption": R.manage_assumptions,
        },
    )

    # --------------------------------------------------
    # Question answering
    # --------------------------------------------------

    builder.add_edge(R.answer_question, R.commit)

    # --------------------------------------------------
    # Research planning
    # --------------------------------------------------

    builder.add_edge(R.propose_questions, R.request_user_input)
    builder.add_edge(R.expand_plan, R.commit)

    # --------------------------------------------------
    # Task management
    # --------------------------------------------------

    builder.add_edge(R.manage_tasks, R.request_user_input)

    # --------------------------------------------------
    # Execution
    # --------------------------------------------------

    builder.add_edge(R.select_task, R.prepare_execution)
    builder.add_edge(R.prepare_execution, R.request_user_input)

    builder.add_edge(R.dispatch_executor, R.review_execution)
    builder.add_edge(R.review_execution, R.review_conflicts)
    builder.add_edge(R.review_conflicts, R.request_user_input)

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

    builder.add_conditional_edges(
        R.process_decision,
        registry.nodes[R.process_decision],
        {
            "clarify": R.understand_request,
            "approved_questions": R.expand_plan,
            "approved_task": R.commit,
            "approved_execution": R.dispatch_executor,
            "approved_conflict": R.commit,
            "cancel": R.commit,
        },
    )

    # --------------------------------------------------
    # Finish
    # --------------------------------------------------

    builder.add_edge(R.commit, END)

    return builder.compile()


