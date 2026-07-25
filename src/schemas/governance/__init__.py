"""Canonical governance contracts package."""

from __future__ import annotations

from schemas.governance.authority import (
    AuthenticatedPrincipal,
    GovernanceAuthority,
    ProposalAuthority,
)
from schemas.governance.decision import GovernanceDecision

__all__ = [
    "AuthenticatedPrincipal",
    "GovernanceAuthority",
    "GovernanceDecision",
    "ProposalAuthority",
]
