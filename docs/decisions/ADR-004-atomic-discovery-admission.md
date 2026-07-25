# ADR-004: Atomic Discovery Admission Transaction Ownership

- **Status**: Accepted `[Implemented]`
- **Context**: Multiple components attempting to create or stage `Discovery` objects introduces race conditions, un-governed claim materialization, and inconsistent evaluation control states.
- **Decision**: `AtomicDiscoveryAdmissionService` (`src/application/discovery/admission_service.py`) is the **sole supported transaction owner** for Discovery materialization.
- **Consequences**: Public `DiscoveryRepository.create()` raises `RuntimeError`. SQLite triggers enforce exact proposal consumption and claim identity immutability.
- **Rejected Alternatives**: Repository `create()` methods, direct model insertion in orchestrator.
- **Verification**: `test_discovery_insert_and_private_stage_are_confined_to_cutover_boundary` and `test_discovery_repository_public_create_is_a_hard_failure`.
