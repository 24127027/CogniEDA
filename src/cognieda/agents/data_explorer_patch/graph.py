from langgraph.graph import END, START
from langgraph.graph.state import CompiledStateGraph, StateGraph


from .context import Context
from .state import State
from .nodes import planning, execute, check_result, _route_after_check_result

def build_graph() -> CompiledStateGraph[State, Context, State, State]:
    builder = StateGraph(
        State,
        context_schema=Context,
    )

    builder.add_node("planning", planning)
    builder.add_node("execute", execute)
    builder.add_node("check_result", check_result)

    builder.add_edge(START, "planning")
    builder.add_edge("planning", "execute")
    builder.add_edge("execute", "check_result")

    builder.add_conditional_edges(
        "check_result",
        _route_after_check_result,
        {
            "planning": "planning",
            END: END,
        },
    )

    return builder.compile()