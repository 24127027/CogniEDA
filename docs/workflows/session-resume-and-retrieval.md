# Session Resume & Retrieval Workflow

> **Status**: `[Implemented]` / `[Verified on SQLite]`

This guide documents workspace session initialization, active context building, and state reconstruction.

---

## 1. Workflow Summary

```text
Workspace Open / Session Resume
└──> SessionFrame Initialization (SessionFrameRecord)
     └──> Context Building (SessionContextBuilder)
          ├──> Filter Invalidated Objects
          ├──> Enforce Assumption Quarantine
          └──> Assemble Active Focal Window
```

---

## 2. Step-by-Step Specification

1. **Preconditions**: SQLite database initialized; existing workspace session ID provided.
2. **Inputs**: Workspace URI, session ID.
3. **Responsible Components**: `SessionContextBuilder` (`src/memory/session_frame.py`), `SessionFrameRepository` (`src/repositories/research/session_frame.py`).
4. **Durable Writes**: Updated `SessionFrameRecord` timestamp and active focal handles.
5. **Resulting State**: Active context window loaded into memory for planner and execution operations.
