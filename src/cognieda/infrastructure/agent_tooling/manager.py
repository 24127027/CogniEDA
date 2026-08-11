import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Any, TypedDict

from pydantic_ai import FunctionToolset
from pydantic_ai.mcp import MCPToolset
from pydantic_ai_skills import SkillsCapability

from cognieda.application.ports import AgentTool, ToolingConfig
from cognieda.infrastructure.mcp import load_mcp_toolsets
from cognieda.infrastructure.skills import load_skills

# Example configuration for agents.toml:
# [planner]
# skills = ["planner"]      # Points to skills/planner/
# mcp = [
#     "filesystem",
#     "neo4j",
# ]

# [graph_miner]
# skills = ["graph_miner"]
# mcp = [
#     "neo4j",
# ]


class WorkerConfig(TypedDict, total=False):
    skills: list[str]
    mcp: list[str]


DEFAULT_WORKER_CONFIG: dict[str, WorkerConfig] = {
    "planner": {},
    "data_explorer": {},
    "graph_miner": {},
    "hypothesis_analyst": {},
}


class AgentTooling:
    def __init__(
        self,
        config: dict[str, WorkerConfig],
        mcp_toolsets: dict[str, MCPToolset[Any]],
        skills: dict[str, SkillsCapability],
    ) -> None:
        self.config = config
        self.mcp_toolsets = mcp_toolsets
        self.skills = skills

    @classmethod
    def load(
        cls,
        tooling_config: ToolingConfig,
    ) -> "AgentTooling":
        config = {worker: values.copy() for worker, values in DEFAULT_WORKER_CONFIG.items()}
        try:
            with open(tooling_config.agents_config_path, "rb") as f:
                loaded_config = tomllib.load(f)
                config.update(loaded_config)
        except FileNotFoundError:
            pass

        mcp_toolsets: dict[str, MCPToolset[Any]] = {}
        if Path(tooling_config.mcp_config_path).exists():
            mcp_toolsets = load_mcp_toolsets(tooling_config.mcp_config_path)

        skills: dict[str, SkillsCapability] = {}
        if Path(tooling_config.skills_config_path).exists():
            skills = load_skills(tooling_config.skills_config_path)

        return cls(config=config, mcp_toolsets=mcp_toolsets, skills=skills)

    def toolsets_for(
        self,
        worker: str,
        builtin_tools: Sequence[AgentTool],
    ) -> list[FunctionToolset[Any] | MCPToolset[Any]]:
        if worker not in self.config:
            raise ValueError(f"Unknown worker '{worker}'.")

        toolsets: list[FunctionToolset[Any] | MCPToolset[Any]] = []

        #
        # Built-in tools
        #
        if builtin_tools:
            toolsets.append(FunctionToolset(tuple(builtin_tools)))

        #
        # MCP toolsets
        #
        worker_cfg = self.config.get(worker, {})

        for server_name in worker_cfg.get("mcp", []):
            try:
                toolsets.append(self.mcp_toolsets[server_name])
            except KeyError as error:
                raise ValueError(
                    f"MCP server '{server_name}' is not defined in mcp.toml."
                ) from error

        return toolsets

    def skills_for(self, worker: str) -> list[SkillsCapability]:
        """Get skills for the given worker."""
        worker_cfg = self.config.get(worker, {})
        configured_skills = worker_cfg.get("skills", [])

        #DEBUG: Log the configured skills for the worker
        print(f"Worker '{worker}' configured skills: {configured_skills}")
        return [self.skills[skill] for skill in configured_skills]
