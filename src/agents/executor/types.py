from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai.messages import ModelMessage
from .capabilities import Capability


# from schemas.artifacts import (
#     DataProfile,
#     Discovery,
#     Evidence,
#     Hypothesis,
#     Task,
# )

# TODO: Uncomment the above import once the schemas are implemented.
#  For now, we define placeholder classes to avoid import errors.
class DataProfile(BaseModel):
    ...
class Discovery(BaseModel):
    ...
class Evidence(BaseModel):
    ...
class Hypothesis(BaseModel):
    ... 
class Task(BaseModel):
    ... 


class ExecutorInput(BaseModel):
    """Shared input for executor invocation."""

    model_config = ConfigDict(extra="forbid")

    task: Task


class ExecutorContext(BaseModel):
    """Shared context available to executors."""

    model_config = ConfigDict(extra="forbid")

    # Add only context fields genuinely shared by executors.


class BaseState(BaseModel):
    """Shared executor graph state."""

    model_config = ConfigDict(extra="forbid")

    task: Task
    messages: list[ModelMessage] = Field(default_factory=list)


class ExecutionRequest(BaseModel):
    """Request sent through the executor dispatcher."""

    model_config = ConfigDict(extra="forbid")

    capability: Capability
    input: ExecutorInput
    context: ExecutorContext


class ExecutionResult(BaseModel):
    """Result returned from a bounded executor invocation."""

    model_config = ConfigDict(extra="forbid")

    hypothesis: Hypothesis | None = None
    evidence: Evidence | None = None
    discoveries: list[Discovery] = Field(default_factory=list)
    data_profile: DataProfile | None = None