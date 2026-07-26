# Events — Target Design

> **Role:** Package technical reference. **Canonical concept owner:**
> [Product surface and bootstrap boundary](../../../docs/product-surface-and-bootstrap-boundary.md).
> **Contributor entry:** [Contributor documentation](../../../docs/development/index.md).
> **Current-state owner:** [CogniEDA current state](../../../docs/current-state.md).

## Current implementation

This directory contains no Python event types, event bus or handlers. Current orchestration uses direct function/service calls and durable database records, not an application event system.

## Target design

A future event layer may publish immutable post-commit facts to loosely coupled handlers. It must not become an alternate writer for `ExecutionRun`, outbox/inbox state, `Evidence`, `Discovery` or other records whose write ownership is already governed.
