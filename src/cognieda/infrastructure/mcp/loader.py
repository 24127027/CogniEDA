import tomllib
from pathlib import Path

from fastmcp.client.transports import StdioTransport
from pydantic_ai.mcp import MCPToolset


def load_mcp_toolsets(path: Path) -> dict[str, MCPToolset]:
    """
    Load all MCP servers defined in mcp.toml.

    Relative paths are resolved relative to the location of mcp.toml.
    """

    config_path = path.resolve()

    with config_path.open("rb") as f:
        config = tomllib.load(f)

    base_dir = config_path.parent

    toolsets: dict[str, MCPToolset] = {}

    for name, cfg in config.items():
        transport = cfg.get("transport")
        if transport is None:
            raise ValueError(
                f"MCP server '{name}' is missing required key 'transport'."
            )

        if transport == "stdio":
            command = cfg.get("command")
            if not command:
                raise ValueError(
                    f"MCP server '{name}' is missing required key 'command'."
                )

            if not Path(command).is_absolute():
                command = str((base_dir / command).resolve())

            toolsets[name] = MCPToolset(
                StdioTransport(
                    command=command,
                    args=cfg.get("args", []),
                    env=cfg.get("env"),
                )
            )

        elif transport == "http":
            url = cfg.get("url")
            if not url:
                raise ValueError(
                    f"MCP server '{name}' is missing required key 'url'."
                )

            toolsets[name] = MCPToolset(url)

        else:
            raise ValueError(
                f"Unsupported transport '{transport}' for MCP server '{name}'."
            )

    return toolsets