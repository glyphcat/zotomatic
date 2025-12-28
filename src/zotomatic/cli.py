"""Command-line interface entry point for zotomatic."""

from __future__ import annotations

import argparse
import sys
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
        prog="zotomatic",
        description="Zotomatic command-line interface",
        add_help=False,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("ready", help="Generate the next ready note")
    subparsers.add_parser("doctor", help="Inspect project health")
    init = subparsers.add_parser(
        "init", help="Initialize a Zotomatic workspace"
    )
    init.add_argument(
        "--pdf-dir",
        dest="pdf_dir",
        required=True,
        help="Directory containing PDF files",
    )
    init.add_argument(
        "--note-dir",
        dest="note_dir",
        help="Directory for generated notes",
    )
    init.add_argument(
        "--template-path",
        dest="template_path",
        help="Path to the note template",
    )
    template = subparsers.add_parser(
        "template", help="Manage note templates"
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


def _print_help() -> None:
    print("Zotomatic command-line interface")
    print("")
    print("Usage:")
    print("  zotomatic <command> [options]")
    print("")
    print("Commands:")
    print("  ready                 Generate the next ready note")
    print("  doctor                Inspect project health")
    print("  init                  Initialize a Zotomatic workspace")
    print("  template create       Create a template and update config")
    print("  template set          Update config to use an existing template")
    print("")
    print("Options:")
    print("  -h, --help            Show this help message and exit")
    print("")
    print("Command options:")
    print("  init:")
    print("    --pdf-dir PATH      (required) Directory containing PDF files")
    print("    --note-dir PATH     Override default note directory")
    print("    --template-path PATH  Override default template path")
    print("  template create/set:")
    print("    --path PATH         (required) Template file path")


def _normalize_cli_options(namespace: argparse.Namespace) -> dict[str, Any]:
    cli_options = {
        key: value
        for key, value in vars(namespace).items()
        if key not in {"command", "template_command"}
    }
    return {key: value for key, value in cli_options.items() if value is not None}


def main(argv: Sequence[str] | None = None) -> None:
    parser = _build_parser()
    args_list = list(argv) if argv is not None else sys.argv[1:]
    if not args_list or "-h" in args_list or "--help" in args_list:
        _print_help()
        return
    args = parser.parse_args(args_list)

    # Run pipelines.
    handlers: dict[str, Any] = {
        "ready": pipelines.run_ready,
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
