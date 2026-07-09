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

`nodes.py` registers all target node names. Most node bodies are still skeletons. `route_intent` and `process_decision` raise `NotImplementedError`.

`src/agents/planner/types.py` defines structured planner state and draft payload models for Task, Objective, Assumption, and conflict-flag operations. `manage_tasks`, `manage_objective`, `manage_assumptions`, and `review_conflicts` translate those structured payloads into `PlannerOperation` objects without mutating persistent FCO state.

`src/application/orchestrator/planner_commit.py` is intentionally skeleton-first. It filters approved/not-required operations, dispatches to placeholder handlers for the supported operation types, marks successfully dispatched persisted operations committed, and returns `PlannerCommitResult`. Approved `UPDATE_OBJECTIVE` operations now create minimal `ObjectiveRevision` provenance when the Objective actually changes. This remains skeleton commit behavior, not production transaction machinery; rollback, approval UX, objective merge policy, and richer provenance belong at this boundary later.

## Node Status

| Node | Target responsibility | Current behavior | Status |
| --- | --- | --- | --- |
| `understand_request` | Interpret latest user message without SessionFrame context. | Registered stub with docstring and `pass`. | Partially implemented |
| `route_intent` | Route to answer, suggest, manage task, execute, objective, or assumption. | Raises `NotImplementedError`. | Partially implemented |
| `answer_question` | Answer using SessionFrame context. | Registered stub with `pass`. | Partially implemented |
| `propose_questions` | Propose directions/open questions. | Registered stub with `pass`. | Partially implemented |
| `expand_plan` | Expand directions into executable tasks and subtasks. | Registered stub with `pass`. | Partially implemented |
| `manage_tasks` | Produce task hierarchy operations. | Converts structured Task create/update/state-change payloads into `PlannerOperation` drafts without direct mutation. | Partially implemented |
| `select_task` | Resolve selected task. | Registered stub with `pass`. | Partially implemented |
| `prepare_execution` | Check readiness, compile hypothesis when appropriate, choose executor. | Registered skeleton with comments; no Hypothesis or executor runtime behavior. | Partially implemented |
| `dispatch_executor` | Delegate to specialist agent. | Registered placeholder with `pass`. | Partially implemented |
| `review_execution` | Review results and prepare Evidence/Discovery/Task/SessionFrame operations. | Registered skeleton with comments; it does not author Evidence or Discovery operations yet. | Partially implemented |
| `review_conflicts` | Detect conflicts with assumptions or existing knowledge. | Converts structured conflict-flag payloads into `FLAG_OBJECT` operations; automatic detection is not implemented. | Partially implemented |
| `manage_objective` | Create objective revision operations. | Converts structured Objective update payloads into `UPDATE_OBJECTIVE` operations. Commit can create minimal `ObjectiveRevision` provenance for real changes. | Partially implemented |
| `manage_assumptions` | Create assumption operations. | Converts structured Assumption create/status payloads into operations without using Assumptions as inference premises. | Partially implemented |
| `request_user_input` | Prepare user approval/clarification request. | Registered stub with `pass`. | Partially implemented |
| `pause` | Pause for user input. | Registered stub with `pass`. | Partially implemented |
| `process_decision` | Route after user decision. | Raises `NotImplementedError`. | Partially implemented |
| `commit` | Persist approved state changes through the operation boundary. | Persists in-memory operations when a database URL exists, then calls `commit_planner_operations`. Current commit is a skeleton dispatch boundary, not full rollback/transaction machinery. | Partially implemented |

## Graph Wiring

`src/agents/planner/graph.py` wires the nodes using LangGraph:

- `START -> understand_request -> route_intent`
- conditional routing from `route_intent`
- user approval loop through `request_user_input -> pause -> process_decision`
- selected approved routes to `commit` or `dispatch_executor`
- `commit -> END`

This wiring matches the target pipeline shape, but behavior is not implemented.

## Known Deviations

- Planner request interpretation, routing, approval UX, task selection, and executor dispatch remain scaffold-level.
- `commit` only supports the current skeleton operation subset and does not implement production rollback, objective merge policy, or approval provenance.
- Execution dispatch has no implemented executor integration.
- `Discovery` FCO schema/table/repository exists, but `review_execution` does not create pending Discovery operations.
