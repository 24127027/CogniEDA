# Artifact Mirrors

This directory contains reviewable metadata mirror templates. Current durable
repository records use the configured SQLModel store, verified on SQLite;
these files are not a second source of truth. No graph-database integration or
composed runtime is currently supported.

Current mirror surface:

- `artifacts/data_profiles/`: `DataProfile` JSON mirror templates for profiled dataset versions.

DataProfile mirrors store dataset identity directly. There is no separate dataset artifact in the research ontology.
