"""Command-line interface entry point for zotomatic."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import Any

from . import api


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zotomatic", description="Zotomatic command-line interface"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "--config-path", dest="config_path", help="Override path to config file"
    )
    shared.add_argument(
        "--output-dir", dest="output_dir", help="Directory for generated artifacts"
    )

    ready = subparsers.add_parser(
        "ready", parents=[shared], help="Generate the next ready note"
    )
    ready.add_argument(
        "--note-title", dest="note_title", help="Title for the generated note"
    )
    ready.add_argument(
        "--note-body", dest="note_body", help="Body content for the generated note"
    )

    subparsers.add_parser("backfill", parents=[shared], help="Process historical items")
    # TODO: add options for backfill, e.g. limit, since, etc.
    subparsers.add_parser("doctor", parents=[shared], help="Inspect project health")
    subparsers.add_parser(
        "init", parents=[shared], help="Initialize a Zotomatic workspace"
    )

    return parser


def _normalize_cli_options(namespace: argparse.Namespace) -> dict[str, Any]:
    cli_options = {
        key: value for key, value in vars(namespace).items() if key != "command"
    }
    return {key: value for key, value in cli_options.items() if value is not None}


def main(argv: Sequence[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    handlers: dict[str, Any] = {
        "ready": api.run_ready,
        "backfill": api.run_backfill,
        "doctor": api.run_doctor,
        "init": api.run_init,
    }

    command = args.command
    cli_options = _normalize_cli_options(args)

    handler = handlers[command]
    handler(cli_options)


if __name__ == "__main__":  # pragma: no cover
    main()
