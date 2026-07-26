# From runtime composition to atomic persistence

This workflow follows one approved scientific proposal from deployment-supplied
runtime dependencies to atomic Discovery admission. It illustrates operational
ownership without repeating the full scientific-authority narrative.

> **Implementation status:** The in-process delegation, durable authority
> reconstruction, claim/fencing protocol, exact proposal-copy, atomic
> scientific cutover, rollback, and replay paths are **Implemented** and
> **Verified on SQLite**. Automatic background coordination and a supported
> product entry point are **Unsupported**.

## The operational path

```text
deployment-supplied dependencies
        |
        v
in-process runtime composition
        |
        v
AtomicDiscoveryAdmissionService
        |
        v
repository staging + guarded lifecycle updates
        |
        v
SQLModel persistence mapping
        |
        v
SQLite transaction, constraints, and selected triggers
        |
        +--> commit complete state
        |
        +--> roll back every effect
                  |
                  v
        later exact replay or recovery
```

Each arrow changes responsibility. The deployment selects adapters. The runtime
assembles and delegates. The application service owns the transaction.
Repositories stage bounded persistence effects. SQLModel maps physical records.
SQLite supplies the currently verified transaction and constraint behavior.

## Preconditions already in durable state

Before admission, the observation and evaluation paths have already produced:

- an eligible terminal analytical Task and its Hypothesis;
- admitted Evidence and AnalysisFrame provenance;
- a repository-built protected evaluation bundle;
- an EvaluationControl containing the exact scientific proposal;
- a principal-bound GovernanceAuthority; and
- an approved ProposalDecision for that exact proposal.

The runtime does not recreate those facts from conversation or caller payload.
The admission service reconstructs them from durable repositories.

## 1. Deployment supplies the runtime dependencies

An external factory chooses the SQLite URL, authenticated-principal resolver,
Hypothesis Analyst model, Data Explorer adapter factory, and execution-context
factory. `runtime_loader` imports that configured factory and rejects missing or
wrongly typed composition.

At this stage no scientific row is changed. A missing adapter fails closed.

## 2. Runtime composition opens persistence

`CogniEDARuntime` invokes canonical database initialization, creates its
process-local registry and Planner, and exposes a Discovery-admission
coordinator facade.

Initialization may upgrade a supported existing database, create missing
current tables, install selected triggers, and run legacy quarantine. Runtime
construction is therefore not a pure object-graph operation, but it still does
not execute pending scientific work automatically.

## 3. Coordination finds work; the application service owns it

The coordinator can discover a pending admission claim and invoke
`AtomicDiscoveryAdmissionService`. It does not own the cutover.

Claim enqueue and acquisition are small application-owned transitions with
owner, token, lease, and fencing state. The claimed execution then reloads:

- the claim and its current fence;
- the EvaluationControl and authoritative proposal;
- the GovernanceAuthority and ProposalDecision;
- the authenticated principal binding;
- Hypothesis, Task, Evidence, AnalysisFrame, and relevant SessionFrame state;
  and
- request, proposal, bundle, and decision fingerprints.

Caller-supplied scientific text or stale detached objects cannot replace this
reconstruction.

## 4. A guarded write establishes the SQLite cutover

The service performs guarded lifecycle updates before final reconstruction.
On SQLite, the first successful write obtains the writer serialization needed
for the remainder of the local transaction. The service then reloads and
revalidates the authoritative chain under that transaction.

This ordering is a SQLite-specific mechanism. The invariant is that no
concurrent mutation can invalidate the reconstructed authority before the
complete cutover commits. A row-locking backend would need an explicit
replacement design.

## 5. Repositories stage bounded effects

Within the same supplied session, private repository hooks stage:

- the deterministic exact-copy Discovery;
- the admission-claim terminal transition.

The application owner directly constructs and stages the conclusion
SessionFrame because public repository creation rejects conclusion frames. It
also stages guarded transitions for:

- Hypothesis to evaluated;
- the terminal analytical Task to completed;
- EvaluationControl to committed; and
- ProposalDecision consumption.

No repository commits these pieces independently. Public Discovery creation
fails closed specifically to prevent that partial path.

## 6. SQLModel maps; SQLite enforces the current transaction

SQLModel records map the staged objects to physical tables. Foreign keys,
uniqueness, guarded update predicates, and selected claim/decision triggers
provide database-level checks. They supplement rather than replace the
service-owned write set.

If every stage succeeds, the service commits once. The result is a mutually
consistent Discovery, conclusion frame, terminal lifecycle, committed
evaluation, consumed decision, and committed claim.

## 7. Any failure rolls back the complete cutover

A lost CAS, expired or mismatched claim, altered fingerprint, missing
provenance, uniqueness race, trigger rejection, or injected failure aborts the
transaction. None of the staged scientific effects becomes durable.

This prevents states such as:

```text
Discovery exists
but the ProposalDecision remains reusable
```

or:

```text
Task is completed
but no exact evidence-bound Discovery committed
```

## 8. Replay and recovery verify, not repeat blindly

After an uncertain outcome, the same request can be retried. Exact replay
reconstructs the deterministic Discovery identity and verifies every durable
effect, fingerprint, lifecycle transition, conclusion frame, consumed decision,
and committed claim.

An exact committed chain returns the prior result. A same-key request with
different authority or content is a conflict. A partial-looking chain is not
accepted as success. Lease expiry can permit a fenced reclaim, but a stale
worker cannot commit through the newer fence.

## Ownership summary

| Stage | Owner | Boundary protected |
| --- | --- | --- |
| concrete dependencies | deployment factory | no hidden or permissive adapters |
| object graph and facade | `CogniEDARuntime` | one visible in-process composition |
| work discovery | admission coordinator | coordination does not imply write ownership |
| scientific cutover | `AtomicDiscoveryAdmissionService` | one complete authoritative transaction |
| bounded persistence staging | repositories | no independent lifecycle commit |
| physical mapping | SQLModel models | mapping does not become ontology or workflow |
| commit, rollback, constraints | SQLite | current supported atomicity and guard behavior |
| uncertain-outcome handling | application owner | exact replay, conflict, reclaim, and fencing |

## What remains outside this workflow

The repository does not supply a supported CLI, API, daemon, worker scheduler,
production identity provider, distributed transaction, or cross-database
admission guarantee. Those are **Unsupported** deployment possibilities or
**Deferred** design decisions, not hidden parts of the workflow.

## Related canonical concepts

- [Runtime and composition boundary](runtime-and-composition-boundary.md)
- [Persistence and transaction ownership](persistence-and-transaction-ownership.md)
- [SQLite boundary and portability](sqlite-boundary-and-portability.md)
- [Database initialization and migrations](database-initialization-and-migrations.md)
- [Governance and Discovery admission](governance-and-discovery-admission.md)

## Implementation orientation

Composition is in `src/application/runtime.py`; admission ownership is in
`src/application/discovery/admission_service.py`; repository staging is under
`src/repositories/discovery/`; physical mapping and initialization are under
`src/db/`. Admission, replay, race, and rollback behavior is exercised under
`tests/application/discovery/` and `tests/e2e/`.
