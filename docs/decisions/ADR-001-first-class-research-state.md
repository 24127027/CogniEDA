# ADR-001: First-Class Research State Model

- **Status**: Accepted `[Implemented]`
- **Context**: Generic LLM assistants treat raw chat history, conversation tokens, and vector database embeddings as knowledge. This leads to epistemic drift, lack of traceability, and invalid analytical conclusions.
- **Decision**: CogniEDA defines 8 explicit, typed First-Class Objects (`Objective`, `DataProfile`, `Assumption`, `Task`, `Hypothesis`, `Evidence`, `Discovery`, `SessionFrame`) with strict schemas, immutability rules, and lifecycles.
- **Consequences**: Unstructured text memory cannot be promoted directly to domain knowledge. All scientific claims must be evidence-bound FCOs.
- **Rejected Alternatives**: Generic chat memory log, raw JSON metadata blobs, vector-only retrieval.
- **Verification**: Architecture tests in `tests/architecture/test_architecture_enforcement.py`.
