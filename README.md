# CogniEDA

## Setup

Prerequisites:

- Python 3.12+
- `uv`

Local setup:

```bash
uv sync
copy .env.example .env
uv run cognieda
```

Verification:

```bash
uv run pytest
uv run ruff check .
uv run mypy src
```

Temporary smoke check for `pytest`:

    >>> 1 + 1
    2

Current scope:

- Tooling and project configuration are in place for local development.
- Application code, `src/` package contents, and test modules are expected to be added in later steps.
