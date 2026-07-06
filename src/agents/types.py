"""Thin shared envelopes for agent graph contracts."""
from typing import Any

from pydantic import BaseModel
    
# TODO: Put whatever application runtime need here
# Agent needs to extract the information from the graph state to return to the runtime
class RuntimePayload(BaseModel):
    """
    The information an agent returns to the runtime after completing a single
    execution iteration.

    This payload is the stable contract between agents and the runtime. It
    contains externally observable outcomes (such as messages, operations,
    execution requests, or artifacts) while hiding the agent's internal
    workflow state.

    The runtime interprets this payload to persist changes, dispatch further
    execution, update the user interface, or continue orchestration.
    """
    payload: Any # Placeholder for the actual payload data. This can be any type of data that the agent wants to return to the runtime.
    