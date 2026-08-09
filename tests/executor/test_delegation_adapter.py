from __future__ import annotations

import asyncio
from types import SimpleNamespace

from agents.executor import (
    Capability,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutorDispatcher,
    ExecutorRegistry,
)
from schemas.artifacts import Task
from tools.delegation.dataset import invoke_data_capability


class ToolTestProvider:
    async def run(self, request: ExecutionRequest) -> ExecutionResult:
        return ExecutionResult(
            source_role="tool_test_provider",
            task_id=request.input.task.task_id,
            work_id="tool-test:1",
            status=ExecutionStatus.SUCCEEDED,
        )


def test_pydantic_ai_adapter_dispatches_to_registered_provider() -> None:
    registry = ExecutorRegistry()
    registry.register_provider(
        ToolTestProvider,
        capabilities=(Capability.DATA_ANALYSIS,),
    )
    deps = SimpleNamespace(dispatcher=ExecutorDispatcher(registry))
    context = SimpleNamespace(deps=deps)
    task = Task(
        instruction="Count dataset rows.",
    )

    result = asyncio.run(invoke_data_capability(context, task))

    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.source_role == "tool_test_provider"
