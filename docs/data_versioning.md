# Data Versioning Workflow

CogniEDA uses a split responsibility model:

- `Git` stores code, schema contracts, and reviewable analytical metadata under `artifacts/`.
- `DVC` stores version pointers for substantial physical datasets under `data/raw/` and `data/derived/`.
- The local SQLModel store persists the runtime artifact state used by repositories and future services.

## Why this split exists

CogniEDA needs dataset lineage and reproducibility, not just large-file storage.

- `DatasetAsset` records make dataset versions explicit.
- `DataProfile` records capture append-only structural summaries for one dataset version and one method.
- DVC keeps large local files out of normal Git history while preserving a versioned pointer in the repo.
- Runtime services still need a local operational store for first-class artifacts beyond dataset metadata, which is the role of the SQLModel scaffold.

## Directory Map

- `data/raw/`: immutable source snapshots, expected to be tracked with DVC
- `data/derived/`: reproducible derived datasets, also expected to be tracked with DVC when material
- `data/samples/`: small Git-tracked fixtures
- `artifacts/dataset_assets/`: Git-tracked `DatasetAsset` JSON mirrors and examples
- `artifacts/data_profiles/`: Git-tracked `DataProfile` JSON mirrors and examples

## Current Storage Clarification

- Only `DatasetAsset` and `DataProfile` are currently mirrored under `artifacts/` as JSON by default.
- `Project`, `Assumption`, `Hypothesis`, `Evidence`, `DecisionLog`, and `SessionFrame` are still first-class repository concepts, but their current operational persistence lives in the local database scaffold.
- `SessionFrame` is the current concrete persisted form of the broader `Context Frame` idea; it is not mirrored under `artifacts/` by default in this scaffold.

## Recommended Workflow for a New Raw Dataset

1. Copy the raw file into `data/raw/`.
2. Track it with DVC: `dvc add data/raw/<dataset-file>`.
3. Commit the generated `.dvc` metafile and updated `.gitignore`.
4. Create a matching `artifacts/dataset_assets/<dataset-name>_<version>.json`.
5. Profile the dataset and store the resulting `DataProfile` JSON under `artifacts/data_profiles/`.
6. Persist the runtime artifact records through the repository layer when the dataset enters an active investigation.

## Recommended Workflow for a Derived Dataset

1. Generate the derived file under `data/derived/`.
2. Track it with DVC if it is large or operationally important.
3. Create a `DatasetAsset` record with:
   - `kind = "derived"`
   - `upstream_dataset_ids` listing every source asset involved
   - `lineage_steps` describing the transformation sequence
   - a new `version`
4. Create a fresh `DataProfile` if the structure or contents changed materially.
5. Persist the derived dataset and profile into the operational store when they become part of active analysis state.

## Remote Storage

The scaffold does not hard-code a DVC remote because the storage target depends on your environment.

Common choices:

- local shared storage for solo development
- S3 or MinIO for team or server-backed workflows
- Azure Blob or GCS if those are your existing data platforms

After installing the DVC CLI, set a default remote that matches your environment before tracking large datasets.

## Guardrails

- Never overwrite raw data in place.
- Treat `DatasetAsset.version` as a real dataset snapshot label, not a loose note.
- Treat `DatasetAsset` lineage as explicit structured state, not just a prose description.
- Keep sample fixtures in Git only when they are small, non-sensitive, and useful for tests.
- Do not treat a `DataProfile` as a rolling mutable status object; create a new profile snapshot when the dataset version changes.
- Do not confuse Git-tracked metadata mirrors with the runtime operational store; both exist for different reasons.
