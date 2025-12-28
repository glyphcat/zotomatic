"""Command-line interface entry point for zotomatic."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import Any

from zotomatic import pipelines

from . import api

# TODO: verbose対応,dry-run対応
"""
cli.py で --verbose をパース → get_logger(verbose=args.verbose)

そのロガーを api.py や各モジュールに渡す

例外は errors.py のクラスで揃えて投げる

try:
    api.run_ready(config, logger=logger)
except ZotomaticError as e:
    logger.error(f"fatal: {e}")
    sys.exit(1)

"""


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
        "--note-dir",
        dest="note_dir",
        help="Directory for generated notes",
    )
    shared.add_argument(
        "--pdf-dir",
        dest="pdf_dir",
        help="Directory containing PDF files",
    )
    shared.add_argument(
        "--template-path",
        dest="template_path",
        help="Path to the note template",
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
    template = subparsers.add_parser(
        "template", parents=[shared], help="Manage note templates"
    )
    template_subparsers = template.add_subparsers(
        dest="template_command", required=True
    )
    template_create = template_subparsers.add_parser(
        "create", help="Create a template and update config"
    )
    template_create.add_argument(
        "--path", dest="template_path", required=True, help="Template file path"
    )
    template_set = template_subparsers.add_parser(
        "set", help="Update config to use an existing template"
    )
    template_set.add_argument(
        "--path", dest="template_path", required=True, help="Template file path"
    )

    return parser


def _normalize_cli_options(namespace: argparse.Namespace) -> dict[str, Any]:
    cli_options = {
        key: value
        for key, value in vars(namespace).items()
        if key not in {"command", "template_command"}
    }
    return {key: value for key, value in cli_options.items() if value is not None}


def main(argv: Sequence[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    # Run pipelines.
    handlers: dict[str, Any] = {
        "ready": pipelines.run_ready,
        "backfill": pipelines.stub_run_backfill,
        "doctor": pipelines.run_doctor,
        "init": pipelines.run_init,
        "template": None,
    }

    command = args.command
    cli_options = _normalize_cli_options(args)

    if command == "template":
        template_command = args.template_command
        if template_command == "create":
            pipelines.run_template_create(cli_options)
        elif template_command == "set":
            pipelines.run_template_set(cli_options)
        else:  # pragma: no cover - argparse enforces choices
            raise ValueError(f"Unknown template command: {template_command}")
        return

    handler = handlers[command]
    handler(cli_options)


if __name__ == "__main__":  # pragma: no cover
    main()
