# Schema and model map

> **Role:** Technical reference. **Canonical concept owner:**
> [Research-state objects and roles](../../concepts/research-state/objects-and-roles.md).
> **Contributor entry:** [Contributor documentation](../../development/index.md).
> **Current-state owner:** [CogniEDA current state](../../current-state.md).

> **Implementation status:** target ontology `[Implemented]`; several lifecycle and product
> governance surfaces remain `[Partially Implemented]`.

## Target First-Class Objects

Exactly these eight objects are FCOs:

| FCO | Current durable representation | Current lifecycle authority |
| --- | --- | --- |
| `Objective` | schema, table, repository, revision provenance | approved Planner commit |
| `DataProfile` | frozen schema, table, repository | profiler/import bootstrap; validity service for invalidation/supersession |
| `Assumption` | schema, table, repository | Planner commit; planning-only premise |
| `Task` | schema, table, repository | Planner commit; execution/Discovery terminal transitions |
| `Hypothesis` | schema, table, repository | execution admission; Evidence/Discovery/validity transitions |
| `Evidence` | frozen schema, table, repository | atomic Evidence admission; validity service changes lifecycle metadata |
| `Discovery` | frozen schema, table, repository | atomic Discovery admission; validity service changes lifecycle metadata |
| `SessionFrame` | schema, append-oriented table/repository | bootstrap/Planner successor snapshots, Discovery conclusion frame, validity supersession |

## Non-FCO boundaries

- `Workspace`: filesystem and runtime boundary.
- `Question`: user input that may become a `Task`.
- `AnalysisFrame` and `ExecutionRun`: provenance.
- `PlannerOperation`: durable pending workflow mutation.
- `GeneratedView`: runtime/provenance output.
- `EvidenceCacheEntry`: cache design target; no persistence exists.
- `ObjectiveRevision`, approvals, inbox/outbox, evaluation controls, governance records,
  admission claims, user decisions, and validity events: workflow, authority, or provenance.

## Implemented invariants

- `DataProfile` and `Evidence` schema payloads are frozen; lifecycle changes are separate guarded
  metadata transitions.
- one `Task` has at most one `Hypothesis`, enforced by a unique constraint;
- one `Hypothesis` has at most one `Discovery`, enforced by a unique constraint;
- protected evaluation requires an active accepted DataProfile and active Evidence;
- Discovery admission requires same-Hypothesis active Evidence and structured claim, scope, and
  validity basis;
- parent Tasks create neither Hypotheses nor Discoveries and cannot enter the
  execution/evaluation/admission terminal path;
- Assumptions and existing Discoveries cannot enter the protected evaluation bundle.

## Known deviations and partial areas

`[Known Deviation]` The Planner currently authors the operational analytical contract; target
design assigns operationalization to Hypothesis Analyst.

`[Partially Implemented]` SessionFrame is append-oriented and has deterministic projections, but
general user item governance, workspace/session cardinality, and refresh/resume UI are absent.

`[Partially Implemented]` Repository methods still provide some bootstrap CRUD surfaces. Exact
scientific writers are sealed, but the project does not claim a general graph-domain abstraction.
