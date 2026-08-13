# Workspace and repository ownership

The CogniEDA repository or installation contains product code and development
resources. A `Workspace` is the user research project selected with
`cognieda [PATH]`; it is not the source checkout and it is not an FCO.

## Physical ownership

The conventional layout is:

```text
my-study/
|-- data/                     # user-owned research material
|   |-- raw/                  # optional source/admitted datasets
|   `-- derived/              # optional authorized successor datasets
`-- .cognieda/                # CogniEDA-owned operational state
    |-- project.toml
    |-- planner.md            # optional project-specific Planner guidance
    |-- state/                # created when a state owner needs it
    `-- sessions/             # created when a session owner needs it
```

**Implemented.** `Workspace.open()` normalizes the selected root with user
expansion and absolute resolution. `Workspace.data_dir`, `state_dir`, and
`session_dir` derive only from that normalized root. Initialization eagerly
creates `<workspace>/.cognieda/project.toml`, the current agent-tooling TOML
files, and `<workspace>/data/`; `planner.md`, `raw/`, `derived/`, `state/`, and
`sessions/` remain optional or lazy.

`data/` is user-visible research material. `.cognieda/` is private operational
configuration and state. `.cognieda/data/` is not a canonical dataset
location.

## Dataset location is not admission

`<workspace>/data/` is a convention, not a universal containment rule. An
explicit absolute path outside the Workspace remains loadable by the current
dataset adapter. Future admission may also accept reviewed relative or
external paths, including paths managed by a separate DVC project.

Filesystem presence never creates a DataProfile or authoritative research
state. A physical dataset and its immutable DataProfile are distinct. Any
cleaning or transformation that changes data must create a successor physical
dataset and successor DataProfile; `data/derived/` is not an ungoverned scratch
directory.

Data Explorer retains exclusive direct dataset access. Workspace path
selection does not authorize Planner or another role to inspect files.

## Repository and integration boundaries

The product root has no `data/`, `artifacts/`, `.dvc/`, or `.dvcignore`
research-project surface. Tests create datasets in temporary test-owned paths;
future tracked dataset fixtures belong under `tests/fixtures/datasets/`.

Root `config/*.toml` files remain development examples. Installed runtime
bootstrap reads optional agent tooling configuration only from the selected
Workspace's `.cognieda/` directory.

**Implemented.** Planner runtime instructions have separate ownership from
repository coding-agent instructions. CogniEDA always retains its source-owned
built-in Planner authority baseline. Optional workspace guidance from
`.cognieda/planner.md` supplements that baseline before the operation-specific
instruction. The instruction utility resolves the direct caller module's
sibling `instruction/` directory; callers do not register or pass their own
instruction paths. A Workspace-root `AGENTS.md` is not read as product Planner
input.

DVC execution is **Unsupported**. The fail-closed
`cognieda.infrastructure.dvc` adapter remains an integration boundary, but the
product repository is not itself a DVC research project.

Workspace-bound persistent research state is **Deferred**. The current SQLite
helper is not composed into `Workspace` or runtime bootstrap and retains a
provisional package-local default unless `COGNIEDA_DB_URL` is supplied. It must
not be described as Workspace-local persistence.
