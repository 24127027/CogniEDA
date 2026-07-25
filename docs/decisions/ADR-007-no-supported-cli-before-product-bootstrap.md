# ADR-007: No Supported CLI Before Product Bootstrap

**Status:** Accepted; current product-surface constraint.

## Context

A placeholder command or daemon would imply an operable product while required
authentication, adapter, worker, and lifecycle composition remains external.

## Decision

The current package exposes no supported CLI, HTTP service, or worker daemon.
`CogniEDARuntime` is an in-process composition root and
`COGNIEDA_RUNTIME_FACTORY` selects an external factory.

## Consequences

Tests and ad hoc scripts are not product entry points. A future product phase
must introduce an authenticated, fail-closed bootstrap without bypassing
existing transaction owners.

## Rejected alternatives

A mock CLI and placeholder API/worker processes.

## Enforcement

`test_supported_package_has_no_cli_surface` in
`tests/architecture/test_architecture_enforcement.py` checks packaged entry
points and forbidden modules. Runtime fail-closed behavior is covered by
`tests/application/test_runtime_composition.py`.
