"""Thin shared envelopes for agent graph contracts."""

from pydantic import BaseModel


# TODO: Put whatever application runtime need here
# Agent needs to extract the information from the graph state to return to the runtime
class RuntimePayload(BaseModel):
    """
    Result returned by an agent after one execution iteration.

    For the MVP, payload is intentionally generic. Agents may return their
    own Pydantic models, and the runtime can inspect them before deciding
    what to do next.
    """

    payload: BaseModel
