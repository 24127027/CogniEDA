from pydantic_ai.tools import RunContext

from ..dependencies.protocols import HasGraphRepository


def create_graph_toolset(ctx: RunContext[HasGraphRepository]) -> None:
    """
    Dummy builtin graph tool for testing purposes.
    """
    return None
