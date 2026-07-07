from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage
from typing import Sequence

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