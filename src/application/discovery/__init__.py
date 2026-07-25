"""Discovery admission bounded context."""

from __future__ import annotations

from application.discovery.admission_coordinator import DiscoveryAdmissionCoordinator
from application.discovery.admission_plan import (
    DISCOVERY_ADMISSION_CONTRACT_VERSION,
    DISCOVERY_ADMISSION_NAMESPACE,
    build_discovery_admission_plan,
    compute_admission_fingerprint,
    generate_deterministic_discovery_id,
)
from application.discovery.admission_service import (
    AtomicDiscoveryAdmissionConflictError,
    AtomicDiscoveryAdmissionError,
    AtomicDiscoveryAdmissionService,
    DiscoveryAdmissionConflictError,
    DiscoveryAdmissionError,
)
from schemas.discovery import AtomicDiscoveryAdmissionResult, DiscoveryAdmissionLease

__all__ = [
    "AtomicDiscoveryAdmissionConflictError",
    "AtomicDiscoveryAdmissionError",
    "AtomicDiscoveryAdmissionResult",
    "AtomicDiscoveryAdmissionService",
    "DISCOVERY_ADMISSION_CONTRACT_VERSION",
    "DISCOVERY_ADMISSION_NAMESPACE",
    "DiscoveryAdmissionConflictError",
    "DiscoveryAdmissionCoordinator",
    "DiscoveryAdmissionError",
    "DiscoveryAdmissionLease",
    "build_discovery_admission_plan",
    "compute_admission_fingerprint",
    "generate_deterministic_discovery_id",
]
