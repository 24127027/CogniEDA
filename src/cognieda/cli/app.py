"""Installed command-line entrypoint for the CogniEDA Planner REPL."""

from __future__ import annotations

import asyncio
from argparse import ArgumentParser, Namespace
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from .main import repl
from .renderer import Renderer

if TYPE_CHECKING:
    from cognieda.runtime import Application


def bootstrap_application(workspace_path: Path) -> Application:
    """Load runtime composition only after command-line parsing succeeds."""
    from cognieda.runtime import bootstrap_application as bootstrap

    return bootstrap(workspace_path)


def build_parser() -> ArgumentParser:
    """Build the CLI parser without initializing application services."""
    parser = ArgumentParser(description="CogniEDA CLI")
    parser.add_argument(
        "--mode",
        choices=("real", "mock"),
        default="real",
        help="Run the real planner runtime or the mock UI playground",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=Path.cwd(),
        type=Path,
        help="Workspace path (defaults to the current working directory)",
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> Namespace:
    """Parse command-line arguments before application bootstrap."""
    return build_parser().parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)

    if args.mode == "mock":
        from .mock_application import MockApplication

        app = MockApplication(workspace_root=args.path)
    else:
        app = bootstrap_application(args.path)

    asyncio.run(repl(app, Renderer())) #type: ignore
