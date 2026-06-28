from pathlib import Path
import tomllib
from typing import TypedDict

from pydantic_ai import FunctionToolset
from pydantic_ai.mcp import MCPToolset

from .mcp.loader import load_mcp_toolsets
from .registry import registry

# from .builtin.graph import search_graph
# from .builtin.workspace import create_task, update_session_frame

# Example configuration for agents.toml:
# [planner]
# mcp = [
#     "filesystem",
#     "neo4j",
# ]

# [graph_miner]
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
    mcp: list[str]


class ToolManager:

    def __init__(
        self,
        config: dict[str, WorkerConfig],
        mcp_toolsets: dict[str, MCPToolset],
    ):
        self.config = config
        self.mcp_toolsets = mcp_toolsets

    @classmethod
    def from_config_path(
        cls,
        path: str | Path = "config/agents.toml",
        mcp_path: str | Path = "config/mcp.toml",
    ) -> "ToolManager":

        with open(path, "rb") as f:
            config: dict[str, WorkerConfig] = tomllib.load(f)

        return cls(
            config=config,
            mcp_toolsets=load_mcp_toolsets(mcp_path),
        )

    def toolsets_for(
        self,
        worker: str,
    ) -> list[FunctionToolset | MCPToolset]:

        if worker not in self.config:
            raise ValueError(
                f"Unknown worker '{worker}'."
            )

        toolsets: list[FunctionToolset | MCPToolset] = []

        #
        # Built-in tools
        #
        builtin = WORKER_BUILTIN_TOOLS.get(worker)

        if builtin:
            toolsets.append(
                registry.create_toolset(builtin)
            )

        #
        # MCP toolsets
        #
        worker_cfg = self.config[worker]

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


tool_manager = ToolManager.from_config_path()