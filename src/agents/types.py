"""Thin shared envelopes for agent graph contracts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AgentEnvelope(BaseModel):
    """Minimal shared run envelope across orchestration and execution agents."""

    run_id: str | None = None
    session_id: str | None = None
    trace_id: str | None = None
    workspace_ref: str | None = None


class BaseState(BaseModel):
    """Base class for graph state objects."""


class RuntimePayload(BaseModel):
    """Opaque payload for infrastructure-only handoff points."""

    payload: Any
