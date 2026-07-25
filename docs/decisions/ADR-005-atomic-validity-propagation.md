# ADR-005: Atomic Validity Propagation Transaction Ownership

- **Status**: Accepted `[Implemented]`
- **Context**: Partial or un-coordinated invalidation of upstream data or hypotheses leaves orphaned, invalid scientific claims active in retrieval contexts.
- **Decision**: `AtomicValidityPropagationService` (`src/application/validity/propagation_service.py`) is the **sole supported transaction owner** for issuing validity events and updating dependent target states.
- **Consequences**: Validity events are immutable and append-only. Dependent target entities (`AnalysisFrame`, `Hypothesis`, `DiscoveryAdmissionClaim`) are atomically updated to `INVALIDATED`.
- **Rejected Alternatives**: In-place deletion of invalid objects, un-monitored cascading updates.
- **Verification**: `test_package_s2b_dependency_directions_are_enforced` and validity propagation tests.
