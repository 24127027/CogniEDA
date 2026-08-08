import asyncio
from argparse import ArgumentParser
from pathlib import Path

from cli import Renderer, repl
from runtime import bootstrap_application


def parse_args():
    parser = ArgumentParser(description="CogniEDA CLI")
    parser.add_argument(
        "path",
        nargs="?",
        default=Path.cwd(),
        type=Path,
        help="Path to execution target (defaults to current working directory)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Pass args.path into bootstrap_application if it accepts a path parameter
    app = bootstrap_application(args.path)
    renderer = Renderer()

    # Start the REPL loop
    asyncio.run(repl(app, renderer))


if __name__ == "__main__":
    main()
