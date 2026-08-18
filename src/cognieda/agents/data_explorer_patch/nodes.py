from .state import State

def planning(state: State) -> State:
    """Planning node of the DataExplorer agent's internal workflow."""
    ...

def execute(state: State) -> State:
    """Execute node of the DataExplorer agent's internal workflow."""
    ...

def check_result(state: State) -> State:
    """Check result node of the DataExplorer agent's internal workflow."""
    ...

def _route_after_check_result(state: State) -> str:
    """Determine the next node after check_result based on the state."""
    ...