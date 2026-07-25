# ADR-002: Assumption Quarantine in Synthesis Contexts

- **Status**: Accepted `[Implemented]`
- **Context**: Analytical assumptions and user heuristics are often used to guide planning. If assumptions leak into hypothesis synthesis, unverified beliefs are treated as empirical facts.
- **Decision**: `Assumption` objects are strictly quarantined and excluded from Conclusion Contexts and Hypothesis Analyst evaluation inputs.
- **Consequences**: Hypotheses can only be evaluated against empirical `Evidence` and verified `DataProfile` records. Contradiction flagging occurs post-admission and does not alter claim validity.
- **Rejected Alternatives**: Including assumptions as soft context prompts, merging assumptions into discovery claim text.
- **Verification**: `test_package_s2a_dependency_directions_are_enforced` and Analyst context builder tests.
