from langgraph.graph import END, START
from langgraph.graph.state import CompiledStateGraph, StateGraph

from .nodes import R, registry, route_entry, route_intent, route_process_decision
from .types import Context, State


def build_graph() -> CompiledStateGraph[State, Context, State, State]:
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
        {
            "understand_request": R.understand_request,
            "resume_planner_operations": R.resume_planner_operations,
        },
    )

    # --------------------------------------------------
    # Intent routing
    # --------------------------------------------------

    builder.add_conditional_edges(
        R.understand_request,
        route_intent,
        {
            "answer": R.answer_question,
            "suggest": R.propose_questions,
            "manage_task": R.manage_tasks,
            "execute": R.select_task,
            "objective": R.manage_objective,
            "assumption": R.manage_assumptions,
            "invalid_request": R.invalid_request,
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
    builder.add_edge(R.expand_plan, R.request_user_input)
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
    builder.add_edge(R.resume_planner_operations, R.process_decision)

    builder.add_conditional_edges(
        R.process_decision,
        route_process_decision,
        {
            "approved_questions": R.expand_plan,
            "approved_task": R.commit,
            "approved_plan": R.commit,
            "approved_conflict": R.commit,
            "approved_execution": R.dispatch_executor,
            "cancel": R.commit,
            "end": END,
        },
    )

    # --------------------------------------------------
    # Finish
    # --------------------------------------------------

    builder.add_edge(R.invalid_request, END)
    builder.add_edge(R.commit, END)

    return builder.compile()

# if __name__ == "__main__":
    # agent_graph = build_graph()
    # agent_graph.get_graph().draw_mermaid_png(output_file_path="graph.png")
