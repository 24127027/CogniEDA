# Planner Workflow

## Target Design

The target planner is a state-operation pipeline. Nodes should produce `PlannerOperation` records, then `commit` should atomically persist approved operations.

Target pipeline:

```text
understand_request
route_intent
answer_question
propose_questions
expand_plan
manage_tasks
select_task
prepare_execution
dispatch_executor
review_execution
review_conflicts
manage_objective
manage_assumptions
request_user_input
pause
process_decision
commit
```

## Current Implementation

Current files inspected:

- `src/agents/planner/nodes.py`
- `src/agents/planner/graph.py`
- `src/agents/planner/types.py`
- `src/agents/planner/agent.py`

`nodes.py` registers all target node names. The request parser and route selection are implemented for explicit commands. A narrow injected-executor execution spine is also implemented: it selects an active terminal analytical Task with an accepted DataProfile, prepares a contract, requires a matching approval snapshot, persists the Hypothesis and pending ExecutionRun before dispatch, validates raw executor output before admitting Evidence, and creates a Discovery only when the executor explicitly requests finalization.

`src/agents/planner/types.py` defines structured planner state and draft payload models for Task, Objective, Assumption, and conflict-flag operations. `manage_tasks`, `manage_objective`, `manage_assumptions`, and `review_conflicts` translate those structured payloads into `PlannerOperation` objects without mutating persistent FCO state.

`src/application/orchestrator/planner_commit.py` is intentionally skeleton-first. It filters approved/not-required operations, dispatches to placeholder handlers for the supported operation types, marks successfully dispatched persisted operations committed, and returns `PlannerCommitResult`. Approved `UPDATE_OBJECTIVE` operations now create minimal `ObjectiveRevision` provenance when the Objective actually changes. This remains skeleton commit behavior, not production transaction machinery; rollback, approval UX, objective merge policy, and richer provenance belong at this boundary later.

## Node Status

| Node | Target responsibility | Current behavior | Status |
| --- | --- | --- | --- |
| `understand_request` | Interpret latest user message without SessionFrame context. | Parses explicit commands deterministically; ordinary-language classification is delegated to an injected structured model. | Partially implemented |
| `route_intent` | Route to answer, suggest, manage task, execute, objective, or assumption. | Deterministically maps a validated request classification to a graph route. | Partially implemented |
| `answer_question` | Answer using SessionFrame context. | Registered stub with `pass`. | Partially implemented |
| `propose_questions` | Propose directions/open questions. | Registered stub with `pass`. | Partially implemented |
| `expand_plan` | Expand directions into executable tasks and subtasks. | Registered stub with `pass`. | Partially implemented |
| `manage_tasks` | Produce task hierarchy operations. | Converts structured Task create/update/state-change payloads into `PlannerOperation` drafts without direct mutation. | Partially implemented |
| `select_task` | Resolve selected task. | Registered stub with `pass`. | Partially implemented |
| `prepare_execution` | Check readiness, compile hypothesis when appropriate, choose executor. | Validates active terminal analytical Task, accepted DataProfile, variables, specification bindings, and one-Hypothesis lifecycle. Produces an approval-bound contract. | Partially implemented |
| `dispatch_executor` | Delegate to specialist agent. | Invokes only an injected analytical executor after durable contract admission. | Partially implemented |
| `review_execution` | Review results and prepare Evidence/Discovery/Task/SessionFrame operations. | Keeps executor output as an observation, materializes AnalysisFrame provenance, and records run failure/success state. Separate evidence-admission and hypothesis-evaluation nodes decide later mutation operations. | Partially implemented |
| `review_conflicts` | Detect conflicts with assumptions or existing knowledge. | Converts structured conflict-flag payloads into `FLAG_OBJECT` operations; automatic detection is not implemented. | Partially implemented |
| `manage_objective` | Create objective revision operations. | Converts structured Objective update payloads into `UPDATE_OBJECTIVE` operations. Commit can create minimal `ObjectiveRevision` provenance for real changes. | Partially implemented |
| `manage_assumptions` | Create assumption operations. | Converts structured Assumption create/status payloads into operations without using Assumptions as inference premises. | Partially implemented |
| `request_user_input` | Prepare user approval/clarification request. | Creates an execution-approval interaction containing the contract fingerprint. | Partially implemented |
| `pause` | Pause for user input. | State placeholder; no durable cross-process interrupt/resume store exists. | Not implemented as a durable workflow boundary |
| `process_decision` | Route after user decision. | Revalidates an approval against the exact prepared contract, then stores state; a separate routing helper selects the next graph node. | Partially implemented |
| `commit` | Persist approved state changes through the operation boundary. | Persists in-memory operations when a database URL exists, then calls `commit_planner_operations`. Current commit is a skeleton dispatch boundary, not full rollback/transaction machinery. | Partially implemented |

## Graph Wiring

`src/agents/planner/graph.py` wires the nodes using LangGraph:

- `START -> understand_request -> route_intent`
- conditional routing from `route_intent`
- user approval loop through `request_user_input -> pause -> process_decision`
- approved execution routes to `commit_execution_contract -> dispatch_executor`; other approved operation routes go to `commit`
- `commit -> END`

This wiring implements only the narrow injected-executor path described above; most planning, answering, conflict, and durable-resumption behavior remains incomplete.

## Known Deviations

- Approval is held in in-memory Planner state; there is no durable approval record, state-version compare-and-swap, or restart-safe interrupt/resume path.
- Evidence admission validates method, parameters, parameter hash, and frame variable bindings, but it does not yet validate row filters, frame hashes against a durable expected frame, artifact contents, or method-specific diagnostics.
- `commit` remains local SQLModel transaction machinery. It has no migration path, distributed recovery protocol, or concurrency reconciliation for critical lifecycle transitions.
- Conflict comparison and answerability are graph hooks only; the required scope-aware classification and evidence-backed answer surface are not implemented.
