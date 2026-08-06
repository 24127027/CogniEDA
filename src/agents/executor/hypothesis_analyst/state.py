"""Internal state for HypothesisAnalyst executor.

This state NEVER leaves the executor.
It's converted from ExecutionRequest on entry and to ExecutionResult on exit.
"""

from ..types import BaseState


# TODO: Put whatever agent need here
class State(BaseState):
    """State for the Hypothesis Analyst agent.

    Internal state fields for hypothesis analysis workflow.
    This will expand as graph implementation progresses.
    """

    ...
