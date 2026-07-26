# Workspace and DataProfile Workflow

> **Role:** Technical reference. **Canonical concept owner:**
> [Research-state model](../research-state-model.md).
> **Contributor entry:** [Contributor documentation](../development/index.md).
> **Current-state owner:** [CogniEDA current state](../current-state.md).

> **Implementation status:** Partial. Dataset loading and profiling plus immutable
> `DataProfile` persistence are implemented library surfaces. A governed
> workspace-import/acceptance workflow, executable DVC integration, and automatic
> `SessionFrame` binding are not implemented.

## Implemented path

```text
CSV or Parquet path / pandas DataFrame
  -> data.profiling.profile_path or profile_dataframe
  -> DataProfile value
  -> DataProfileRepository.create
  -> immutable data_profiles row
```

- `src/data/loaders.py` loads CSV and Parquet inputs.
- `src/data/profiling.py` derives schema, baseline statistics, quality flags,
  preprocessing history, and source/version identifiers.
- `src/repositories/research/data_profile.py` persists and reads immutable
  `DataProfile` FCOs.
- `DataProfileRepository.supersede` deliberately rejects split-transaction
  supersession. Supersession and dependent invalidation must go through
  `AtomicValidityPropagationService`.

Creating a profile does not imply that a user accepted it as ground truth. The
caller must supply the lifecycle and acceptance state represented by the schema.
No current service combines file registration, review, acceptance, persistence,
and frame creation into one governed product workflow.

## Invariants and failure behavior

- Cleaning or transforming data creates a new dataset version and a new
  `DataProfile`; an existing profile is not rewritten.
- Profiling failures occur before repository persistence.
- Repository writes are ordinary single-record commits, not a cross-object
  workspace transaction.
- `src/data/dvc.py` is an explicit adapter stub and raises
  `DvcIntegrationNotImplementedError`.

## Not yet implemented

- a production CLI/API flow for import, review, acceptance, and cleaning;
- executable DVC commands or automatic dataset-version registration;
- automatic creation or replacement of a `SessionFrame` when a profile is
  accepted.
