from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai.messages import ModelMessage


class Task(BaseModel):
    """Placeholder for a Task object. 
    # TODO: Import the actual Task class later
    """

class Input(BaseModel):
    """Shared input for all executors"""
    task: Task
    ...

class Context(BaseModel):
    """Shared context for all executors"""
    ...

class BaseState(BaseModel):
    """Base state for all executors"""
    task: Task
    messages: Sequence[ModelMessage] = []

class ExecutionRequest(BaseModel):
    """Request to execute a task."""
    input: Input
    context: Context
    capability: str

class ExecutionResult(BaseModel):
    """Result of executing a task."""
    ...


class ExecutorOutput(BaseModel):
    """Executor payload contract returned to the runtime."""

    evidence_drafts: list[Any] = Field(default_factory=list)
    discovery_drafts: list[Any] = Field(default_factory=list)
    execution_run_ref: str | None = None
