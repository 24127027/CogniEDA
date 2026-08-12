from __future__ import annotations

import os
from pathlib import Path

from cognieda.infrastructure.llm import AgentFactory
from cognieda.agents.data_explorer import DataExplorer
from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.application.ports import ModelConfig, ProviderType
from cognieda.execution import Capability, ExecutorDispatcher, ExecutorRegistry
from cognieda.infrastructure.agent_tooling import AgentTooling

from .application import Application
from .workspace import Workspace


def bootstrap_application(workspace_path: Path) -> Application:
    workspace = Workspace.open(workspace_path)
    model_config = resolve_model_config(workspace)

    agent_factory = AgentFactory(tooling_config=workspace)

    registry = ExecutorRegistry()
    registry.register_provider(
        lambda: DataExplorer(config=model_config, agent_factory=agent_factory),
        capabilities=(
            Capability.DATA_ANALYSIS,
            Capability.DATA_PROFILING,
            Capability.DATA_TRANSFORMATION,
        ),
    )
    dispatcher = ExecutorDispatcher(registry)
    planner = Planner(
        deps=PlannerDeps(dispatcher=dispatcher),
        agent_factory=agent_factory,
        model_config=model_config,
        agent_instruction=workspace.load_planner_agent_instruction(),
    )

    return Application(
        agent_factory=agent_factory,
        workspace=workspace,
        planner_agent=planner,
        dispatcher=dispatcher,
    )


def _resolved_value(
    workspace: Workspace,
    key: str,
    *environment_names: str,
) -> str:
    workspace_value = workspace.config.get(key)
    if workspace_value is not None and str(workspace_value).strip():
        return str(workspace_value).strip()

    for environment_name in environment_names:
        environment_value = os.environ.get(environment_name, "").strip()
        if environment_value:
            return environment_value

    return ""


def _normalize_provider(provider: str) -> ProviderType:
    if provider == "gemini":
        return "google"
    if provider == "openai":
        return "openai"
    if provider == "google":
        return "google"
    if provider == "anthropic":
        return "anthropic"
    raise ValueError(f"Unsupported model provider: {provider}")


def resolve_model_config(workspace: Workspace) -> ModelConfig:
    """Resolve workspace-first model configuration without mutating process state."""

    provider = _resolved_value(workspace, "model.provider", "COGNIEDA_MODEL_PROVIDER")
    model_name = _resolved_value(workspace, "model.name", "COGNIEDA_MODEL_NAME")
    base_url = _resolved_value(
        workspace,
        "model.base_url",
        "MODEL_BASE_URL",
        "COGNIEDA_OPENAI_BASE_URL",
    )
    api_key = _resolved_value(
        workspace,
        "model.api_key",
        "MODEL_API_KEY",
        "COGNIEDA_OPENAI_API_KEY",
    )

    if not model_name:
        raise ValueError(
            "Model name is required in .cognieda/project.toml or COGNIEDA_MODEL_NAME."
        )
    if not api_key:
        raise ValueError(
            "Model API key is required in .cognieda/project.toml or "
            "MODEL_API_KEY (legacy fallback: COGNIEDA_OPENAI_API_KEY)."
        )
    if not provider:
        raise ValueError(
            "Model provider is required in .cognieda/project.toml or "
            "COGNIEDA_MODEL_PROVIDER."
        )

    return ModelConfig(
        provider=_normalize_provider(provider),
        model_name=model_name,
        base_url=base_url,
        api_key=api_key,
    )
