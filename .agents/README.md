## Agent Specs

> **Role:** Agent-instruction navigation, not canonical reader or current-state
> documentation. Use the [canonical documentation journey](../docs/index.md),
> [CogniEDA current state](../docs/current-state.md), and
> [Contributor documentation](../docs/development/index.md) before treating an
> instruction as an implementation claim.

This directory holds task-specific agent specifications.

Keep this separate from the repository root `AGENTS.md`:

- `AGENTS.md` defines repository-wide guidance for coding agents working in this codebase.
- `.agents/*.md` defines focused agents for specific analytical roles or workflows.

Current agent specs:

- `eda_analyst.md`: structured exploratory data analysis agent aligned with CogniEDA artifact rules.
- `context_memory_manager.md`: agent-agnostic context and memory curator aligned with SessionFrame and memory-governance rules.
