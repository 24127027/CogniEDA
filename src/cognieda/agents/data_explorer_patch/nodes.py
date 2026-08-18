from langgraph.runtime import Runtime

from .state import State
from .context import Context

def planning(state: State, runtime: Runtime[Context]) -> State:
    """Planning node of the DataExplorer agent's internal workflow."""
    ...

def execute(state: State, runtime: Runtime[Context]) -> State:
    """Execute node of the DataExplorer agent's internal workflow."""
    ...

def check_result(state: State, runtime: Runtime[Context]) -> State:
    """Check result node of the DataExplorer agent's internal workflow."""
    ...

def _route_after_check_result(state: State) -> str:
    """Determine the next node after check_result based on the state."""
    ...