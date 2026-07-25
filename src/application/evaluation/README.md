# Evaluation Application Package (`src/application/evaluation/`)

> Canonical Documentation: [ADR-003: Specialist Scientific Authority](../../docs/decisions/ADR-003-specialist-scientific-authority.md) | [Evidence to Discovery Workflow](../../docs/workflows/evidence-to-discovery.md)

## Purpose
Owns evaluation control state management and protected Hypothesis Analyst execution orchestration.

## Owned Responsibilities
- `EvaluationControlService` (`control_service.py`).
- Assembling protected Conclusion Context for Hypothesis Analyst.
- Managing `EvaluationControlRecord` state transitions (`PENDING` $\rightarrow$ `CLAIMED` $\rightarrow$ `PROPOSAL_READY`).

## Forbidden Responsibilities
- Direct governance decision recording (owned by `application.governance`).
- Discovery materialization (owned by `application.discovery`).
- Injecting `Assumption` objects into evaluation inputs.

## Canonical Inputs / Outputs
- Input: `Evidence`-ready `Hypothesis`, evaluation key.
- Output: `DiscoverySynthesisBundle`, `DiscoveryProposal`.

## Transaction Authority
Sole transaction owner for `EvaluationControlRecord` lifecycle transitions.

## Tests
- `tests/application/evaluation/test_control_service.py`
