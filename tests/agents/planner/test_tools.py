from __future__ import annotations

import asyncio
from typing import cast
from uuid import UUID, uuid4

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

from cognieda.agents.planner.context import PlannerContext
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.agents.planner.tools import RUN_DATA_WORK_TOOL, run_data_work
from cognieda.application.ports import ExecutorDispatcherPort
from cognieda.schemas import (
    DataProfile,
    Evidence,
    EvidenceProvenance,
    Objective,
    Plan,
    PlanTaskBinding,
    Task,
    TaskKind,
)


class RecordingDispatcher:
    async def dispatch(self, request: object) -> object:
        raise AssertionError(f"Fake execution session should own dispatch: {request}")


class RecordingExecutionSession:
    def __init__(
        self,
        *,
        context: PlannerContext,
        task: Task,
        eligible: bool,
        failure: Exception | None,
    ) -> None:
        self.context = context
        self.task = task
        self.eligible = eligible
        self.failure = failure
        self.progress_count = 0
        self.calls: list[tuple[UUID, str]] = []

    async def run_data_work(
        self,
        dispatcher: ExecutorDispatcherPort,
        *,
        task_id: UUID,
        requested_work: str,
    ) -> Evidence:
        del dispatcher
        if task_id != self.task.task_id:
            raise ValueError("outside the approved Plan")
        if not self.eligible:
            raise ValueError("not currently eligible")
        if self.failure is not None:
            raise self.failure
        self.calls.append((task_id, requested_work))
        self.progress_count += 1
        profile = self.context.data_profile
        assert profile is not None
        return Evidence(
            task_id=task_id,
            data_profile_id=profile.data_profile_id,
            content={"requested_work": requested_work},
            provenance=EvidenceProvenance(
                producer_role="data_explorer",
                work_reference=f"work:{len(self.calls)}",
                dataset_reference="dataset:v1",
                data_profile_id=profile.data_profile_id,
            ),
        )


def _scope(
    *,
    enabled: bool = True,
    eligible: bool = True,
    failure: Exception | None = None,
) -> tuple[PlannerDeps, Task, RecordingExecutionSession]:
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
    dispatcher = RecordingDispatcher()
    profile = DataProfile(row_count=10, column_count=0, columns=())
    context = PlannerContext(
        active_plan=plan,
        objective=objective,
        tasks=(task,),
        data_profile=profile,
    )
    execution_session = RecordingExecutionSession(
        context=context,
        task=task,
        eligible=eligible,
        failure=failure,
    )
    deps = PlannerDeps(
        dispatcher=cast(ExecutorDispatcherPort, dispatcher),
        executor_tools_enabled=enabled,
        execution_session=execution_session,
    )
    return deps, task, execution_session


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
    assert "requested_work" in schema_text
    assert "RunContext" not in schema_text
    assert "Capability" not in schema_text
    assert "dispatcher" not in schema_text


def test_tool_rejects_wrong_or_ineligible_task_before_dispatch() -> None:
    deps, task, execution_session = _scope(eligible=False)

    with pytest.raises(ModelRetry, match="not currently eligible"):
        asyncio.run(
            run_data_work(
                _run_context(deps),
                task.task_id,
                "Profile the dataset",
            )
        )
    with pytest.raises(ModelRetry, match="outside the approved Plan"):
        asyncio.run(
            run_data_work(
                _run_context(deps),
                uuid4(),
                "Profile the dataset",
            )
        )
    assert execution_session.calls == []


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
    deps, task, execution_session = _scope()
    request_count = 0

    def model_function(_messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal request_count
        request_count += 1
        if request_count == 1:
            assert [tool.name for tool in info.function_tools] == ["run_data_work"]
            args = {
                "task_id": str(task.task_id),
                "requested_work": "Profile the dataset",
            }
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
    assert len(execution_session.calls) == 2
    tool_returns = [
        part
        for message in result.new_messages()
        for part in message.parts
        if isinstance(part, ToolReturnPart)
    ]
    assert len(tool_returns) == 2
    assert all("requested_work" in str(part.content) for part in tool_returns)
