"""Internal state for HypothesisAnalyst executor.

This state NEVER leaves the executor.
It is built from ExecutorInput on entry; the graph must return the canonical
ExecutorResult envelope on exit.
"""

from ..types import BaseState


# TODO: Put whatever agent need here
class State(BaseState):
    """State for the Hypothesis Analyst agent.

    Internal state fields for hypothesis analysis workflow.
    This will expand as graph implementation progresses.
    """

    ...
