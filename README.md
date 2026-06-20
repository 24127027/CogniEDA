# CogniEDA

CogniEDA is a memory-driven agentic EDA system for deep data investigation and long-running context management. The current concrete contract surface is:

- typed artifact schemas under `src/schemas/`
- a local artifact database scaffold under `src/db/`
- thin artifact-specific repositories under `src/repositories/`
- baseline profiling utilities under `src/data/`
- `SessionFrame` as the current persisted implementation of the broader `Context Frame` concept
- reviewable dataset metadata mirrors under `artifacts/`

## Setup

Prerequisites:

- Python 3.12+
- `uv`

Local setup:

```bash
uv sync
copy .env.example .env
```

Current state:

- The packaged `cognieda` entrypoint is still a scaffold placeholder.
- The durable implementation surface today is the typed schemas, local artifact DB scaffold, repositories, profiling utilities, context-frame contracts, and tests.
- The SQLModel store is the operational runtime source of truth for all first-class artifacts.
- `artifacts/dataset_assets/` and `artifacts/data_profiles/` are Git-tracked metadata mirrors for reviewable dataset lineage and profile snapshots.
- Other first-class artifacts are DB-backed in the current scaffold unless and until an explicit export/import layer is introduced.
- Start from [docs/architecture.md](docs/architecture.md), [docs/artifacts.md](docs/artifacts.md), and [docs/persistence.md](docs/persistence.md) before adding domain services.

Verification:

```bash
uv run pytest
uv run ruff check .
uv run mypy src
```

## Data Versioning Scaffold

The repository now includes a starter layout for dataset versioning and analytical metadata:

- `data/raw/` for immutable source snapshots intended for DVC tracking
- `data/derived/` for reproducible derived datasets
- `data/samples/` for small Git-tracked fixtures
- `artifacts/dataset_assets/` for Git-tracked `DatasetAsset` JSON mirrors
- `artifacts/data_profiles/` for Git-tracked `DataProfile` JSON mirrors

The operational repository layer still persists the full artifact set, including `Project`, `Assumption`, `Hypothesis`, `Evidence`, `DecisionLog`, and `SessionFrame`, in the local database scaffold.

See [docs/data_versioning.md](docs/data_versioning.md) for the expected workflow and the relationship between Git, DVC, and artifact metadata.
