import tomllib
from pathlib import Path

from fastmcp.client.transports import StdioTransport
from pydantic_ai.mcp import MCPToolset

# Example configuration for mcp.toml:
# [filesystem]
# transport = "stdio"
# command = "uvx"
# args = ["mcp-server-filesystem"]
#
# [neo4j]
# transport = "http"
# url = "http://localhost:8000/mcp"

def load_mcp_toolsets(
    path: str | Path = "config/mcp.toml",
) -> dict[str, MCPToolset]:
    """
    Load all MCP servers defined in mcp.toml.

    Example:
        {
            "filesystem": MCPToolset(...),
            "neo4j": MCPToolset(...),
        }
    """

    with open(path, "rb") as f:
        config = tomllib.load(f)

    toolsets: dict[str, MCPToolset] = {}

    for name, cfg in config.items():
        transport = cfg.get("transport")
        if transport is None:
            raise ValueError(f"MCP server '{name}' is missing required key 'transport'.")

        if transport == "stdio":
            # Use StdioTransport from fastmcp for arbitrary terminal/local commands
            command = cfg.get("command")
            if not command:
                raise ValueError(f"MCP server '{name}' is missing required key 'command'.")

            toolsets[name] = MCPToolset(
                StdioTransport(
                    command=command,
                    args=cfg.get("args", []),
                    env=cfg.get("env"),
                )
            )

        elif transport == "http":
            # For HTTP/SSE endpoints, you can pass the URL string directly to MCPToolset
            url = cfg.get("url")
            if not url:
                raise ValueError(f"MCP server '{name}' is missing required key 'url'.")

            toolsets[name] = MCPToolset(url)

        else:
            raise ValueError(
                f"Unsupported transport '{transport}' for MCP server '{name}'."
            )

    return toolsets