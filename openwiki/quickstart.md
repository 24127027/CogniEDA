---
type: Quickstart Guide
title: CogniEDA Quick Start
description: Get up and running with CogniEDA in 5 minutes. Set up your environment, launch the Planner REPL, and explore a basic workflow.
tags: [getting-started, setup, cli, tutorial]
---

# CogniEDA Quick Start

## Prerequisites

- Python 3.12 or later
- `uv` package manager

## Installation

```powershell
# Clone and enter the repository
cd /path/to/CogniEDA

# Install dependencies
uv sync

# Install the CLI tool
uv tool install --editable .

# Set up environment
copy .env.example .env
```

## Configuration

Set your LLM API key in `.env`:

```
MODEL_API_KEY=your_key_here
```

Default model provider is Google. To use OpenAI or Anthropic:

1. Create or edit `.cognieda/project.toml` in your workspace
2. Add: `model.provider = "openai"` or `model.provider = "anthropic"`

## Launch the REPL

```powershell
# Start with default workspace (current directory)
cognieda

# Or specify a workspace path
cognieda C:\path\to\workspace
```

## First Steps

1. **View help**: Type `help` in the REPL
2. **Create an objective**: Plan what you want to analyze
3. **Load data**: Point to a CSV or Parquet file
4. **Generate hypotheses**: Let the system suggest testable claims
5. **Run analysis**: Execute the workflow and view results

## Directory Structure

```
workspace/
├── data/                    # Your datasets
├── .cognieda/              # CogniEDA configuration
│   ├── project.toml        # Workspace settings
│   ├── .cognieda.db        # Local SQLite database
│   └── artifacts/          # Analysis results
└── .env                    # Environment variables (local workspace)
```

## Verification

Run tests to verify installation:

```powershell
uv run pytest
uv run ruff check .
uv run mypy src/cognieda
```

## Next Steps

- Read [System Overview](./architecture/overview.md) for architecture
- Explore [Component Reference](./reference/components.md) for API details
- Check [Development Guide](./development/setup.md) for contributor setup

## Troubleshooting

**Import error**: Ensure `uv sync` completed and tool is installed
**Missing .env**: Copy `.env.example` to `.env` and set `MODEL_API_KEY`
**Database lock**: Delete `.cognieda/.cognieda.db` and restart
**Model API fails**: Verify API key and provider configuration in `.cognieda/project.toml`
