"""Governance bounded context."""

from __future__ import annotations

from application.governance.authority import (
    GOVERNANCE_AUTHORITY_ISSUER_ID,
    USER_GOVERNED_OPERATION_TYPE,
    USER_GOVERNED_PURPOSE,
    AuthenticatedPrincipalResolver,
    GovernanceAuthorityIssuer,
    ProposalAuthorizationError,
)
from application.governance.decision_service import (
    ALLOWED_TRUSTED_OPERATION_TYPES,
    ALLOWED_TRUSTED_PRODUCERS,
    ALLOWED_TRUSTED_PURPOSES,
    DiscoveryAdmissionGovernanceService,
    ProposalDecisionConflictError,
)
from application.governance.fingerprints import (
    DISCOVERY_ADMISSION_CONTRACT_VERSION,
    DISCOVERY_ADMISSION_NAMESPACE,
    compute_admission_fingerprint,
    compute_decision_fingerprint,
    compute_governance_authority_fingerprint,
    generate_deterministic_discovery_id,
)

__all__ = [
    "ALLOWED_TRUSTED_OPERATION_TYPES",
    "ALLOWED_TRUSTED_PRODUCERS",
    "ALLOWED_TRUSTED_PURPOSES",
    "DISCOVERY_ADMISSION_CONTRACT_VERSION",
    "DISCOVERY_ADMISSION_NAMESPACE",
    "GOVERNANCE_AUTHORITY_ISSUER_ID",
    "USER_GOVERNED_OPERATION_TYPE",
    "USER_GOVERNED_PURPOSE",
    "AuthenticatedPrincipalResolver",
    "DiscoveryAdmissionGovernanceService",
    "GovernanceAuthorityIssuer",
    "ProposalAuthorizationError",
    "ProposalDecisionConflictError",
    "compute_admission_fingerprint",
    "compute_decision_fingerprint",
    "compute_governance_authority_fingerprint",
    "generate_deterministic_discovery_id",
]
