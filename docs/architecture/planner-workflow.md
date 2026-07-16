# Planner Workflow

> **Current implementation snapshot:** 2026-07-16. Source graph topology is defined by `src/agents/planner/graph.py`; worker execution after admission lives under `src/application/orchestrator/`.

## Compiled graph currently in source

```text
START
  -> understand_request                 (new request)
  -> resume_execution -> process_decision (resumed approval)

understand_request
  -> contextual_grounding
  -> invalid_request                    (unsupported/invalid command)

contextual_grounding
  -> check_answerability -> answer_question -> commit -> END
  -> propose_questions -> request_user_input -> pause -> process_decision
  -> expand_plan       -> request_user_input -> pause -> process_decision
  -> manage_tasks      -> request_user_input -> pause -> process_decision
  -> select_task -> prepare_execution -> request_user_input -> pause
  -> manage_objective  -> request_user_input -> pause -> process_decision
  -> manage_assumptions-> request_user_input -> pause -> process_decision
  -> review_result / review_conflict -> END

process_decision
  -> commit_execution_contract          (only reachable approved path)
  -> understand_request                 (clarify)
  -> END                                (cancel)
```

The graph does **not** contain application worker dispatch, result receipt, scientific evaluation or finalization nodes.

## Node status

| Node/area | Current implementation | Status |
| --- | --- | --- |
| `understand_request` | Explicit command precedence plus injectable classification model | Partial; default model adapter is broken |
| `contextual_grounding` | No body | Not implemented |
| `check_answerability` | No body | Not implemented |
| `answer_question` | No body | Not implemented |
| `propose_questions` | No body | Not implemented |
| `expand_plan` | No body | Not implemented |
| `manage_tasks` | Converts already-present typed drafts into PlannerOperations | Partial; no public draft producer |
| `select_task` | Selects eligible task from supplied state/context | Implemented local stage |
| `prepare_execution` | Builds/reuses Hypothesis and prepared execution/admission drafts | Implemented narrow stage |
| `manage_objective` / `manage_assumptions` | Convert supplied drafts into operations | Partial; no public draft producer |
| `review_result` / `review_conflict` | Placeholder hooks | Not implemented as detection/review |
| `request_user_input` | Persists durable `ExecutionApproval` for prepared execution | Implemented for execution only |
| `pause` | No body; LangGraph MemorySaver holds in-process graph state | Not a durable general pause boundary |
| `resume_execution` / `process_decision` | Reload and validate execution approval/decision | Implemented for execution only |
| `commit_execution_contract` | Revalidates and atomically admits Hypothesis/Run/Outbox via operations | Implemented narrow stage |
| `commit` | Persists/dispatches approved operations through local SQLModel boundary | Partial general commit |

## Approval reachability deviation

`DECISION_ROUTES` declares `approved_task`, `approved_plan`, and `approved_conflict`, but `route_process_decision()` can return only `approved_execution`, `clarify`, or `cancel`. The graph therefore does not implement general task/plan/conflict approval despite the route names.

## Operation boundary

Planner nodes should produce typed operations rather than mutating durable state. Current commit code provides:

- durable `PlannerOperation` envelopes and repository;
- approved/not-required filtering;
- rollback on apply/flush errors;
- a special atomic execution/scientific bundle;
- handlers for Task, Assumption, Hypothesis, AnalysisFrame, Evidence, Discovery, Objective, SessionFrame and conflict flags.

Known gaps:

- `DELETE_TASK` has no handler;
- outbox-only execution operation can be marked committed without a row;
- Task update payload fields are not fully accepted by `TaskUpdate`;
- direct attempt/inbox writes are rejected because the transition service is the owner;
- public planner output may report requested ids instead of actually committed ids.

## Worker continuation after graph admission

```text
commit_execution_contract -> ExecutionRun + outbox -> END

external worker:
  dispatch_pending_attempts
    -> receive_executor_result
    -> finalize_pending_result
    -> process_scientific_result
```

This split is current implementation, not merely target topology.

## Target design

The broader target pipeline still includes governed answer/planning/conflict workflows, runnable specialist executors, retrieval, user-controlled SessionFrame updates and production checkpointing. Those targets must not be described as live until the graph nodes, external surfaces and tests exist.

