# Hypothesis Analyst Specialist (`agents.executor.hypothesis_analyst`)

> **Role:** Package technical reference. **Canonical concept owner:**
> [Protected evaluation](../../../../docs/concepts/scientific-lifecycle/protected-evaluation.md).
> **Contributor entry:** [Contributor documentation](../../../../docs/development/index.md).
> **Current-state owner:** [CogniEDA current state](../../../../docs/current-state.md).

## 1. Purpose
Hypothesis Analyst is the sole specialist authorized to evaluate a protected scientific `DiscoverySynthesisBundle` and author a structured `DiscoveryProposal` or `EvaluationFailure`.

## 2. Why the package exists
To enforce epistemic discipline by isolating evidence-evaluation reasoning from persistence, chat history, user context, Assumptions, prior Discoveries, and workflow operations.

## 3. Owned authority
- Authoring `DiscoveryProposal` or `EvaluationFailure` from a protected `DiscoverySynthesisBundle`.

## 4. Forbidden responsibilities
- Accessing database sessions, repositories, or raw files.
- Persisting any state.
- Receiving governance authority or recording decisions.
- Consuming Assumptions, prior Discoveries, SessionFrames, chat history, or generic context bags.
- Creating durable Discovery records or updating Hypothesis/Task lifecycle state directly.

## 5. Canonical input and output
- **Input**: `DiscoverySynthesisBundle` (via `HypothesisAnalystDependencies`).
- **Output**: `HypothesisAnalystResult` (`DiscoveryProposal` | `EvaluationFailure`).

## 6. Happy path
```text
DiscoverySynthesisBundle -> evaluate_synthesis_bundle -> DiscoveryProposal
```

## 7. Failure, retry, reclaim, and replay
- Structured output retry bounded by PydanticAI.
- The Analyst may author a typed `EvaluationFailure`; provider/configuration exceptions are
  translated and persisted by `application.evaluation.runner`.
- Durable retry, reclaim, fencing, and replay remain application responsibilities.

## 8. Transaction owner
Hypothesis Analyst has no transaction ownership. Application services in `application.evaluation` manage durable attempt state.

## 9. Exact proposal binding
Proposals are validated against the input bundle via `validate_proposal_against_bundle` before return.

## 10. Tests proving the boundary
- `tests/agents/test_hypothesis_analyst_authority.py`
- `tests/schemas/evaluation/test_evaluation_contracts.py`

## 11. Current limitations
- Requires explicit PydanticAI model provider configuration.

## 12. Deferred work
- No CLI or background loop is included.
