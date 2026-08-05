# Configuration files

These TOML files are development configuration surfaces, not proof of a
working integration.

- `agents.toml` names worker skill and MCP references. Some references do not
  resolve to enabled MCP definitions.
- `mcp.toml` contains commented examples only.
- `skills.toml` declares file-based skill locations; declaration does not prove
  that a runtime role is composed or authorized.

Any future configuration must preserve canonical authority: Planner has no
scientific operationalization authority, Data Explorer exclusively accesses
datasets, Hypothesis Analyst has no direct dataset access, and Graph Miner is
read-only. See [Current state](../docs/status/current-state.md).
