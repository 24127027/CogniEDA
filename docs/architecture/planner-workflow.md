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
  -> commit                             (approved Task-operation batch)
  -> understand_request                 (clarify)
  -> END                                (cancel)
```

The graph does **not** contain application worker dispatch, result receipt, scientific evaluation or finalization nodes.

## Node status

| Node/area | Current implementation | Status |
| --- | --- | --- |
| `understand_request` | Explicit command precedence plus request-only configured classification adapter | Partially implemented; live configuration/model service is external to this repository |
| `contextual_grounding` | No body | Not implemented |
| `check_answerability` | No body | Not implemented |
| `answer_question` | No body | Not implemented |
| `propose_questions` | No body | Not implemented |
| `expand_plan` | No body | Not implemented |
| `manage_tasks` | Produces typed Task-create/update/state PlannerOperations from a configured structured-output adapter, without direct Task persistence | Implemented narrow Task-management scope |
| `select_task` | Selects eligible task from supplied state/context | Implemented local stage |
| `prepare_execution` | Builds/reuses Hypothesis and prepared execution/admission drafts | Implemented narrow stage |
| `manage_objective` / `manage_assumptions` | Convert supplied drafts into operations | Partial; no public draft producer |
| `review_result` / `review_conflict` | Placeholder hooks | Not implemented as detection/review |
| `request_user_input` | Persists durable `ExecutionApproval` for execution and pending PlannerOperations for Task proposals | Implemented for execution and Task-operation approval |
| `pause` | No body; execution and Task-operation resume use their durable records rather than relying on MemorySaver | Not a durable general pause boundary |
| `resume_execution` / `resume_planner_operations` / `process_decision` | Reload and validate execution approval or the exact session-bound Task-operation batch | Implemented for execution and Task-operation approval |
| `commit_execution_contract` | Revalidates and atomically admits Hypothesis/Run/Outbox via operations | Implemented narrow stage |
| `commit` | Persists/dispatches approved operations through local SQLModel boundary | Partial general commit |

## Current approval boundary

`/manage_task` proposals persist pending Task-operation records before the user sees them. The caller must resume with the returned proposal fingerprint and exact ordered operation-id list; the Planner rejects unknown, stale, replayed, cross-session, or mismatched proposals. Approval marks the exact batch approved and commits it atomically. Cancellation, revision, or clarification rejects that batch.

Plan/objective/assumption/conflict approvals remain target design, even though the graph retains route names for those future workflows.

## Operation boundary

Planner nodes should produce typed operations rather than mutating durable state. Current commit code provides:

- durable `PlannerOperation` envelopes and repository;
- approved/not-required filtering;
- rollback on apply/flush errors;
- a special atomic execution/scientific bundle;
- handlers for Task, Assumption, Hypothesis, AnalysisFrame, Evidence, Discovery, Objective, SessionFrame and conflict flags.

Known gaps:

- `DELETE_TASK` has no handler;
- admission rejects malformed run/outbox bundles before either row is staged;
- public Task create/update translation resolves only supplied local references and preserves Task update fields, including supersession;
- direct attempt/inbox writes are rejected because the transition service is the owner;
- public planner output reports only operation IDs returned by the commit result.

## Step status

Steps 1-3, Step 3.5A, and the narrow Step 3.5B execution-attempt correction are complete for the behavior described above. Step 4 is not implemented.

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
