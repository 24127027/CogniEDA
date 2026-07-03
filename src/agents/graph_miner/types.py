"""Graph-miner agent-specific contracts."""

from __future__ import annotations

from pydantic import Field

from agents.types import AgentEnvelope, BaseState


class GraphMinerInput(AgentEnvelope):
    """Input accepted by graph-miner infrastructure."""

    query: str


class GraphMinerOutput(AgentEnvelope):
    """Output produced by graph-miner infrastructure."""

    matches: list[str] = Field(default_factory=list)


class GraphMinerState(BaseState):
    """Internal graph-miner state."""

    input: GraphMinerInput | None = None
    output: GraphMinerOutput | None = None
