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

- Repository session helpers fall back to `.local/cognieda_graph.sqlite3` when
  `COGNIEDA_DB_URL` is empty.
- `CogniEDARuntime` itself requires a non-empty explicit database URL in
  `RuntimeConfiguration`; it does not silently select that fallback.
- SQLite foreign keys are enabled on connect.
- `init_db()` applies ordered targeted upgrades, creates missing current
  SQLModel tables, installs selected guards, and runs legacy quarantine.

See [Database initialization and migrations](../database-initialization-and-migrations.md)
for the supported fresh and existing-database boundary.

Agent LLM behavior:

- `src/agents/llm.py` reads `COGNIEDA_MODEL_NAME`, `COGNIEDA_OPENAI_BASE_URL`, and `COGNIEDA_OPENAI_API_KEY`.
- `COGNIEDA_MODEL_NAME` and `COGNIEDA_OPENAI_API_KEY` are required by `create_agent()`.
- These agent variables are not currently listed in `.env.example`.

## Commands

Product Surface:

CogniEDA exposes no supported CLI product surface.
The codebase is structured as an in-process library and runtime composition root (`src/application/runtime.py`).

See [Runtime and composition boundary](../runtime-and-composition-boundary.md)
for the deployment-supplied factory seam and unsupported product surfaces.

Verification commands:

```powershell
uv run pytest
uv run ruff check .
uv run mypy src
```

Markdown structure, canonical index coverage, relative links, and local heading
anchors are checked by
`tests/architecture/test_documentation_integrity.py`.

## Tool And MCP Config

`config/agents.toml` and `config/skills.toml` contain worker/skill
configuration. `config/mcp.toml` contains only commented examples, so the MCP
names referenced by the checked-in agent configuration are currently
undefined. The configured skill directories also contain no tracked
`SKILL.md` files. `src/tools/manager.py` loads all three surfaces and fails
explicitly on an undefined MCP reference. Supply coherent deployment
configuration before using model-backed configured Planner adapters. The
exported graph/dataset built-ins remain placeholders.

## Current verification note

Verification counts are checkout-specific. The current S4 command evidence and
known strict-mypy debt are recorded in the ignored local audit referenced by the
[Structural Exit Status](../architecture/structural-exit-status.md); rerun the
commands before making a release claim.
