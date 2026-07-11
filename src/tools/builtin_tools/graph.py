from pydantic_ai.tools import RunContext
from ..dependencies.protocols import HasGraphRepository

def create_graph_toolset(ctx: RunContext[HasGraphRepository]) -> dict:
    """
    Dummy builtin graph tool for testing purposes.
    """
    ...

    