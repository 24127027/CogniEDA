# ADR-007: No Supported CLI Entry Point Before Product Bootstrap

- **Status**: Accepted `[Implemented]`
- **Context**: Introducing premature CLI or web service wrappers before completing the underlying research-state transaction engine creates false product expectations and maintenance overhead.
- **Decision**: CogniEDA will **not package a production CLI entry point**, HTTP service, or worker daemon before Package 7 product bootstrap.
- **Consequences**: `pyproject.toml` contains no `console_scripts` or `py-modules = ["main"]`. Internal test helpers in `tests/` are not supported application entry points.
- **Rejected Alternatives**: Mock CLI shell, placeholder REST API daemon.
- **Verification**: `test_supported_package_has_no_cli_surface` in `tests/architecture/test_architecture_enforcement.py`.
