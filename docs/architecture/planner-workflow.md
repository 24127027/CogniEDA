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

`nodes.py` registers all target node names. Most node bodies are `pass`. `route_intent` and `process_decision` raise `NotImplementedError`. `PlannerState`, `PlannerRequest`, and `PlannerResult` are empty subclasses. `Planner.before_run()` and `Planner.after_run()` are not implemented.

## Node Status

| Node | Target responsibility | Current behavior | Status |
| --- | --- | --- | --- |
| `understand_request` | Interpret latest user message without SessionFrame context. | Registered stub with docstring and `pass`. | Partially implemented |
| `route_intent` | Route to answer, suggest, manage task, execute, objective, or assumption. | Raises `NotImplementedError`. | Partially implemented |
| `answer_question` | Answer using SessionFrame context. | Registered stub with `pass`. | Partially implemented |
| `propose_questions` | Propose directions/open questions. | Registered stub with `pass`. | Partially implemented |
| `expand_plan` | Expand directions into executable tasks and subtasks. | Registered stub with `pass`. | Partially implemented |
| `manage_tasks` | Produce task hierarchy operations. | Registered stub with docstring saying it should produce operations. No operation model exists. | Partially implemented |
| `select_task` | Resolve selected task. | Registered stub with `pass`. | Partially implemented |
| `prepare_execution` | Check readiness, compile hypothesis when appropriate, choose executor. | Registered stub with `pass`. | Partially implemented |
| `dispatch_executor` | Delegate to specialist agent. | Registered stub with `pass`. | Partially implemented |
| `review_execution` | Review results and prepare Evidence/Discovery/Task/SessionFrame operations. | Registered stub with `pass`. | Partially implemented |
| `review_conflicts` | Detect conflicts with assumptions or existing knowledge. | Registered stub with `pass`. | Partially implemented |
| `manage_objective` | Create objective revision operations. | Registered stub with `pass`; no `Objective` model exists. | Partially implemented |
| `manage_assumptions` | Create assumption operations. | Registered stub with `pass`. | Partially implemented |
| `request_user_input` | Prepare user approval/clarification request. | Registered stub with `pass`. | Partially implemented |
| `pause` | Pause for user input. | Registered stub with `pass`. | Partially implemented |
| `process_decision` | Route after user decision. | Raises `NotImplementedError`. | Partially implemented |
| `commit` | Atomically persist approved state changes. | Registered stub with `pass`; no `PlannerOperation` model exists. | Partially implemented |

## Graph Wiring

`src/agents/planner/graph.py` wires the nodes using LangGraph:

- `START -> understand_request -> route_intent`
- conditional routing from `route_intent`
- user approval loop through `request_user_input -> pause -> process_decision`
- selected approved routes to `commit` or `dispatch_executor`
- `commit -> END`

This wiring matches the target pipeline shape, but behavior is not implemented.

## Known Deviations

- No `Task` FCO exists, so task management is target-only.
- No `PlannerOperation` schema exists, so operation-before-commit is target-only.
- `commit` does not persist anything.
- Execution dispatch has no implemented executor integration.
- `review_execution` cannot create `Discovery` because `Discovery` is not implemented.
