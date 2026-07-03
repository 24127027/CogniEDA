from pathlib import Path
import tomllib
from typing import TypedDict

from pydantic_ai import FunctionToolset
from pydantic_ai.mcp import MCPToolset
from pydantic_ai_skills import SkillsCapability

from .mcp.loader import load_mcp_toolsets
from .skills.loader import load_skills
from .registry import registry

# from .builtin.graph import search_graph
# from .builtin.workspace import create_task, update_session_frame

# Example configuration for agents.toml:
# [planner]
# skills = ["planner"]      # Points to skills/planner/# 
# mcp = [
#     "filesystem",
#     "neo4j",
# ]

# [graph_miner]
# skills = ["graph_miner"] 
# mcp = [
#     "neo4j",
# ]

#
# Built-in application architecture
#
WORKER_BUILTIN_TOOLS = {
    "planner": [
        # search_graph,
        # create_task,
        # update_session_frame,
    ],
    "graph_miner": [
        # search_graph,
    ],
    "hypothesis_analyst": [
        # run_pearson,
        # run_ttest,
    ],
}


class WorkerConfig(TypedDict, total=False):
    skills: list[str]
    mcp: list[str]


class ToolManager:

    def __init__(
        self,
        config: dict[str, WorkerConfig],
        mcp_toolsets: dict[str, MCPToolset],
        skills: dict[str, SkillsCapability]
    ):
        self.config = config
        self.mcp_toolsets = mcp_toolsets
        self.skills = skills

    @classmethod
    def from_config_path(
        cls,
        path: str | Path = "config/agents.toml",
        mcp_path: str | Path = "config/mcp.toml",
        skills_path: str | Path = "config/skills.toml"
    ) -> "ToolManager":
        config: dict[str, WorkerConfig] = {}
        try:
            with open(path, "rb") as f:
                config = tomllib.load(f)
        except FileNotFoundError:
            pass

        mcp_toolsets: dict[str, MCPToolset] = {}
        if Path(mcp_path).exists():
            mcp_toolsets = load_mcp_toolsets(mcp_path)

        skills: dict[str, SkillsCapability] = {}
        if Path(skills_path).exists():
            skills = load_skills(skills_path)

        return cls(config=config, mcp_toolsets=mcp_toolsets, skills=skills)

    def toolsets_for(
        self,
        worker: str,
    ) -> list[FunctionToolset | MCPToolset]:

        if worker not in self.config and worker not in WORKER_BUILTIN_TOOLS:
            raise ValueError(f"Unknown worker '{worker}'.")

        toolsets: list[FunctionToolset | MCPToolset] = []

        #
        # Built-in tools
        #
        builtin = WORKER_BUILTIN_TOOLS.get(worker)

        if builtin:
            toolsets.append(registry.create_toolset(builtin))

        #
        # MCP toolsets
        #
        worker_cfg = self.config.get(worker, {})

        for server_name in worker_cfg.get("mcp", []):

            try:
                toolsets.append(
                    self.mcp_toolsets[server_name]
                )

            except KeyError:
                raise ValueError(
                    f"MCP server '{server_name}' is not defined in mcp.toml."
                )

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
    skills_path: str | Path = "config/skills.toml"
) -> None:
    global tool_manager
    tool_manager = ToolManager.from_config_path(
        path=path, 
        mcp_path=mcp_path,
          skills_path=skills_path
    )