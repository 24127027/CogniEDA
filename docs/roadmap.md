# CogniEDA Development Roadmap

> **Implementation status:** Packages S1-S3 are present in the reviewed source.
> Package S4 is the current documentation/structural-exit checkpoint. Package 7
> is a future product slice and has not started.

This roadmap distinguishes reviewed implementation from target work. Commit
history names are useful provenance, but source and tests determine current
behavior.

## Structural foundation

| Package | Reviewed outcome |
| --- | --- |
| Gate 0 | Core FCO schemas, SQLite initialization, and scientific-safety baseline. The `wave-1-sqlite-integration` tag points to `9b46c204eb4eed85c39b726bdce105ac5eac74a7`. |
| S1-A | Private Data Explorer registry/dispatcher boundary and fail-closed runtime composition. |
| S1-B | Execution transitions, recovery, and atomic Evidence admission separated into application contexts. The canonical class is `ExecutionAttemptTransitionService`. |
| S2-A | Protected evaluation and governance separated; the Analyst authors proposals but cannot authorize or persist Discoveries. |
| S2-B | Atomic Discovery admission and atomic validity propagation established as sole supported transaction owners. |
| S3-A/S3-B | Canonical persistence model modules normalized behind the explicit 21-table `db.models` facade; SQLite migration/trigger tests cover the supported boundary. |
| S4 | Canonical documentation reconstructed and adversarially reconciled with source, tests, migrations, and Git history. Final limitations are recorded in the structural-exit report. |

## Package 7 readiness

The S4 verdict is **READY WITH EXPLICIT LIMITATIONS**, not a claim that a product
surface already exists. Package 7 may build a narrow end-to-end product slice
provided it preserves these boundaries:

- Data Explorer remains observation-only.
- Hypothesis Analyst receives only `DiscoverySynthesisBundle` and returns a
  typed proposal/failure.
- user authority and exact proposal decisions precede Discovery admission;
- only the existing atomic services materialize Evidence, Discovery, and
  validity effects;
- Assumptions remain excluded from conclusion synthesis;
- proposed/non-terminal Tasks cannot execute or produce scientific claims.

Likely product work includes an authenticated CLI/API bootstrap, a production
Data Explorer adapter and worker loop, the governed dataset/profile workflow,
and completion of Planner branches. The Planner's direct SQLModel/repository
knowledge is documented non-blocking debt; introducing an application facade is
preferred when that surface is touched.

## Deferred work

- executable DVC/artifact integration and governed cleaning;
- Graph Miner traversal plus persistent semantic/vector indexing;
- validity-keyed Evidence cache;
- multi-tenant service/worker deployment and production model/auth adapters;
- broader reproducibility envelope, CI policy, and strict-mypy remediation.

See [Implementation Gap Analysis](architecture/implementation-gap-analysis.md)
for the current gap inventory and
[Structural Exit Status](architecture/structural-exit-status.md) for the S4
verdict.
