# Workspace & DataProfile Workflow

> **Status**: `[Implemented]` / `[Verified on SQLite]`

This guide documents the lifecycle, preconditions, responsible components, and failure modes for workspace initialization and immutable dataset profiling.

---

## 1. Workflow Summary

```text
Dataset File / Raw Source
└──> Data Profiler
     └──> Statistical Fingerprinting & Validation
          └──> DataProfile Record (Immutable)
               └──> Active SessionFrame Binding
```

---

## 2. Step-by-Step Specification

1. **Preconditions**: Raw CSV/Parquet dataset present in workspace `data/raw/` directory.
2. **Inputs**: File path, workspace ID, dataset name.
3. **Responsible Components**: Data Profiler Service (`src/schemas/research/data_profile.py`, `src/repositories/research/data_profile.py`).
4. **Durable Writes**: `DataProfileRecord` created in SQLite `data_profiles` table (`accepted_as_ground_truth=1`).
5. **Failure / Retry / Replay**: If profiling fails due to corrupted data or invalid schema, no `DataProfileRecord` is written. Retry requires providing a corrected data file.
6. **User Governance Points**: User accepts `DataProfile` as ground truth.
7. **Resulting State**: Immutable `DataProfile` available for planning and execution contexts.
8. **Immutability Enforcement**: Any subsequent data cleaning or transformation generates a **new dataset version** and a **new `DataProfile`**. Existing profiles are never updated in place.
