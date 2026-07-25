# ADR-003: Specialist Scientific Authority Separation

- **Status**: Accepted `[Implemented]`
- **Context**: Allowing code-execution agents to formulate scientific claims leads to ungrounded prose and unverified discoveries.
- **Decision**: Separate specialist authority completely: Data Explorer has observation authority only; Hypothesis Analyst is the sole author of scientific proposals (`DiscoveryProposal`). Neither agent has persistence or decision authority.
- **Consequences**: Code execution output cannot directly become a Discovery. Hypothesis Analyst cannot execute code or access raw conversation history.
- **Rejected Alternatives**: Monolithic scientist agent, code execution script generating discovery markdown files.
- **Verification**: `test_package_s1a_generic_executor_symbols_are_absent_from_active_code` and Specialist contract tests.
