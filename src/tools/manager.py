import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Any, TypedDict

from pydantic_ai import FunctionToolset
from pydantic_ai.mcp import MCPToolset
from pydantic_ai_skills import SkillsCapability

from .builtin_tools import AvailableBuiltinTools
from .mcp.loader import load_mcp_toolsets
from .skills.loader import load_skills

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


class ToolManager:
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
    def from_config_path(
        cls,
        path: str | Path = "config/agents.toml",
        mcp_path: str | Path = "config/mcp.toml",
        skills_path: str | Path = "config/skills.toml",
    ) -> "ToolManager":
        config: dict[str, WorkerConfig] = {}
        try:
            with open(path, "rb") as f:
                config = tomllib.load(f)
        except FileNotFoundError:
            pass

        mcp_toolsets: dict[str, MCPToolset[Any]] = {}
        if Path(mcp_path).exists():
            mcp_toolsets = load_mcp_toolsets(mcp_path)

        skills: dict[str, SkillsCapability] = {}
        if Path(skills_path).exists():
            skills = load_skills(skills_path)

        return cls(config=config, mcp_toolsets=mcp_toolsets, skills=skills)

    def toolsets_for(
        self,
        worker: str,
        builtin_tools: Sequence[AvailableBuiltinTools],
    ) -> list[FunctionToolset[Any] | MCPToolset[Any]]:
        if worker not in self.config:
            raise ValueError(f"Unknown worker '{worker}'.")

        toolsets: list[FunctionToolset[Any] | MCPToolset[Any]] = []

        #
        # Built-in tools
        #
        if builtin_tools:
            toolsets.append(FunctionToolset(tuple(tool.function for tool in builtin_tools)))

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

        return [self.skills[skill] for skill in configured_skills]


tool_manager: ToolManager | None = None


def initialize_tool_manager(
    path: str | Path = "config/agents.toml",
    mcp_path: str | Path = "config/mcp.toml",
    skills_path: str | Path = "config/skills.toml",
) -> ToolManager:
    global tool_manager
    tool_manager = ToolManager.from_config_path(
        path=path,
        mcp_path=mcp_path,
        skills_path=skills_path,
    )
    return tool_manager
