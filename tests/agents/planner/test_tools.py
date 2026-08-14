from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from pydantic_ai import Agent, ModelRetry, RunContext, RunUsage
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.agents.planner.tools import RUN_DATA_WORK_TOOL, run_data_work
from cognieda.execution import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutorContext,
)
from cognieda.schemas import Objective, Plan, PlanTaskBinding, Task, TaskKind


class RecordingDispatcher:
    def __init__(self, *, failure: Exception | None = None) -> None:
        self.requests: list[ExecutionRequest] = []
        self.failure = failure

    async def dispatch(self, request: ExecutionRequest) -> ExecutionResult:
        self.requests.append(request)
        if self.failure is not None:
            raise self.failure
        return ExecutionResult(
            source_role="data_explorer",
            task_id=request.input.task.task_id,
            work_id=f"work:{len(self.requests)}",
            status=ExecutionStatus.SUCCEEDED,
        )


def _scope(
    *,
    enabled: bool = True,
    eligible: bool = True,
    failure: Exception | None = None,
) -> tuple[PlannerDeps, Task, RecordingDispatcher]:
    objective = Objective(text="Understand retention data.")
    task = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Profile the retained dataset.",
    )
    plan = Plan.create(
        objective=objective,
        task_bindings=(PlanTaskBinding(task_id=task.task_id, order_rank=0),),
        tasks=(task,),
    )
    dispatcher = RecordingDispatcher(failure=failure)
    deps = PlannerDeps(
        dispatcher=dispatcher,
        executor_tools_enabled=enabled,
        approved_plan=plan,
        approved_tasks=(task,),
        eligible_task_ids=frozenset({task.task_id}) if eligible else frozenset(),
        execution_context=ExecutorContext(dataset_path="C:/data/retention.csv"),
    )
    return deps, task, dispatcher


def _run_context(deps: PlannerDeps) -> RunContext[PlannerDeps]:
    return RunContext(deps=deps, model=TestModel(), usage=RunUsage())


def test_dynamic_prepare_hides_tool_before_approval_and_schema_is_semantic() -> None:
    disabled, _, _ = _scope(enabled=False)
    enabled, _, _ = _scope()

    hidden = asyncio.run(RUN_DATA_WORK_TOOL.prepare_tool_def(_run_context(disabled)))
    visible = asyncio.run(RUN_DATA_WORK_TOOL.prepare_tool_def(_run_context(enabled)))

    assert hidden is None
    assert visible is not None
    assert visible.name == "run_data_work"
    schema_text = str(visible.parameters_json_schema)
    assert "task_id" in schema_text
    assert "work" in schema_text
    assert "RunContext" not in schema_text
    assert "Capability" not in schema_text
    assert "dispatcher" not in schema_text


def test_tool_rejects_wrong_or_ineligible_task_before_dispatch() -> None:
    deps, _, dispatcher = _scope(eligible=False)

    with pytest.raises(ModelRetry, match="not currently eligible"):
        asyncio.run(
            run_data_work(
                _run_context(deps),
                next(iter(deps.approved_plan.task_ids)),  # type: ignore[union-attr]
                "profile_dataset",
            )
        )
    with pytest.raises(ModelRetry, match="outside the approved Plan"):
        asyncio.run(
            run_data_work(
                _run_context(deps),
                uuid4(),
                "profile_dataset",
            )
        )
    assert dispatcher.requests == []


def test_dispatch_failure_is_a_controlled_model_retry() -> None:
    deps, task, _ = _scope(failure=RuntimeError("provider unavailable"))

    with pytest.raises(ModelRetry, match="Data Explorer dispatch failed"):
        asyncio.run(
            run_data_work(
                _run_context(deps),
                task.task_id,
                "profile_dataset",
            )
        )


def test_one_agent_run_supports_multiple_semantic_tool_calls_and_retains_returns() -> None:
    deps, task, dispatcher = _scope()
    request_count = 0

    def model_function(_messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal request_count
        request_count += 1
        if request_count == 1:
            assert [tool.name for tool in info.function_tools] == ["run_data_work"]
            args = {"task_id": str(task.task_id), "work": "profile_dataset"}
            return ModelResponse(
                parts=[
                    ToolCallPart("run_data_work", args, tool_call_id="first"),
                    ToolCallPart("run_data_work", args, tool_call_id="second"),
                ]
            )
        return ModelResponse(parts=[TextPart("Reviewed both Data Explorer results.")])

    agent = Agent(
        FunctionModel(model_function),  # type: ignore[arg-type]
        tools=(RUN_DATA_WORK_TOOL,),
        deps_type=PlannerDeps,
    )
    result = agent.run_sync("Execute the approved DATA Task.", deps=deps)

    assert result.output == "Reviewed both Data Explorer results."
    assert len(dispatcher.requests) == 2
    tool_returns = [
        part
        for message in result.new_messages()
        for part in message.parts
        if isinstance(part, ToolReturnPart)
    ]
    assert len(tool_returns) == 2
    assert all("data_explorer" in str(part.content) for part in tool_returns)
