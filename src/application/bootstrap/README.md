# Bootstrap — Target Design

> **Role:** Package technical reference. **Canonical concept owner:**
> [Product bootstrap](../../../docs/operations/product-bootstrap.md).
> **Contributor entry:** [Contributor documentation](../../../docs/development/index.md).
> **Current-state owner:** [CogniEDA current state](../../../docs/current-state.md).

## Current implementation

This directory contains no Python bootstrap implementation. The current
in-process composition root is `src/application/runtime.py`, with external
factory loading in `src/application/runtime_loader.py`. There is no
`dependency_container.py`, worker bootstrap, or startup lifecycle here.

The canonical current boundary is
[Runtime composition](../../../docs/operations/runtime-composition.md).
The product-process inventory and minimum coherent bootstrap are owned by
[Product bootstrap](../../../docs/operations/product-bootstrap.md).

## Target design

A future bootstrap package may:

- load validated configuration;
- create database/session factories;
- initialize the tool manager and executor registry;
- construct planner and worker services;
- expose explicit application/worker entrypoints.

Do not add phantom modules to architecture diagrams or runtime documentation before they exist and are tested.
