# Development Setup

## Prerequisites

- Python 3.12+
- `uv`

## Install

From the repository root:

```powershell
uv sync
copy .env.example .env
```

## Environment

Current `.env.example` contains:

```text
COGNIEDA_ENV=local
COGNIEDA_LOG_LEVEL=INFO
COGNIEDA_DB_URL=
COGNIEDA_DB_ECHO=false
```

Database behavior:

- If `COGNIEDA_DB_URL` is empty, the default SQLite URL points to `.local/cognieda_graph.sqlite3`.
- SQLite foreign keys are enabled on connect.
- `init_db()` creates all SQLModel tables.

Agent LLM behavior:

- `src/agents/llm.py` reads `COGNIEDA_MODEL_NAME`, `COGNIEDA_OPENAI_BASE_URL`, and `COGNIEDA_OPENAI_API_KEY`.
- `COGNIEDA_MODEL_NAME` and `COGNIEDA_OPENAI_API_KEY` are required by `create_agent()`.
- These agent variables are not currently listed in `.env.example`.

## Commands

Current package script:

```powershell
uv run cognieda
```

Current result: the script runs `main.py`, which prints a placeholder message.

This verifies packaging only. It does not start the planner, database, worker, API, or UI.

Verification commands:

```powershell
uv run pytest
uv run ruff check .
uv run mypy src
```

No docs build or docs link-check command was found in the current repo.

## Tool And MCP Config

`config/agents.toml` and `config/skills.toml` contain worker/skill configuration. `config/mcp.toml` is primarily commented examples. `src/tools/manager.py` loads all three surfaces. The exported graph/dataset built-ins remain placeholders.

## Current verification note

At the 2026-07-16 source snapshot, full pytest passes (210 tests), while Ruff reports 12 findings and strict mypy reports 132 errors. The default natural-language planner adapter also calls `create_agent()` with an invalid signature.
