# Tools package

The tools package is **Partially implemented** as assembly plumbing and
**Unsupported** as an external integration surface.

`ToolManager` can load configured skills, resolve configured MCP definitions,
and combine caller-selected built-in toolsets. Current graph and dataset
built-ins are placeholders, configured MCP worker references do not have
enabled server definitions, and no end-to-end runtime proves a working
external tool path.

Tool availability never grants scientific or admission authority. In the
canonical target, Data Explorer alone receives dataset access, Graph Miner is
read-only, and Hypothesis Analyst receives no dataset tool.

See [Authority boundaries](../../docs/architecture/authority-boundaries.md) and
[Current state](../../docs/status/current-state.md).
