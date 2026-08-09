"""Installed command-line entrypoint for the CogniEDA Planner REPL."""

from __future__ import annotations

import asyncio
from argparse import ArgumentParser, Namespace
from collections.abc import Sequence
from pathlib import Path

from cognieda.runtime import bootstrap_application

from .main import repl
from .renderer import Renderer


def build_parser() -> ArgumentParser:
    """Build the CLI parser without initializing application services."""
    parser = ArgumentParser(description="CogniEDA CLI")
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
    """Open the selected workspace and run the Planner REPL."""
    args = parse_args(argv)
    app = bootstrap_application(args.path)
    asyncio.run(repl(app, Renderer()))
