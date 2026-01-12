"""Command-line interface entry point for zotomatic."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import Any

from zotomatic import __version__, pipelines
from zotomatic.errors import ZotomaticCLIError, ZotomaticError

from . import api

# TODO: verbose対応,dry-run対応


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zotomatic",
        description="Zotomatic command-line interface",
        add_help=False,
    )
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=__version__,
        help="Show version and exit",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Scan for PDFs and generate notes")
    scan_mode = scan.add_mutually_exclusive_group()
    scan_mode.add_argument(
        "--once",
        action="store_true",
        help="Scan existing PDFs once and exit",
    )
    scan_mode.add_argument(
        "--watch",
        action="store_true",
        help="Watch for new PDFs (default)",
    )
    scan_mode.add_argument(
        "--path",
        nargs="+",
        help=(
            "Generate notes for specific PDF paths (processed in order) and exit; "
            "useful for PDFs not in Zotero"
        ),
    )
    scan.add_argument(
        "--force",
        action="store_true",
        help="Rescan PDFs and generate missing notes, ignoring watcher state",
    )
    scan.add_argument(
        "--summary-mode",
        dest="llm_summary_mode",
        choices=["quick", "standard", "deep"],
        help="Override summary mode for this scan only (quick, standard, deep)",
    )
    config_parser = subparsers.add_parser("config", help="Manage configuration values")
    config_subparsers = config_parser.add_subparsers(dest="config_command")
    config_subparsers.add_parser("show", help="Show effective configuration values")
    config_subparsers.add_parser("default", help="Reset config to defaults")
    config_subparsers.add_parser(
        "migrate", help="Migrate config values to the latest schema"
    )
    subparsers.add_parser("doctor", help="Inspect project health")
    init = subparsers.add_parser("init", help="Initialize a Zotomatic workspace")
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
    init.add_argument(
        "--llm-provider",
        dest="llm_provider",
        choices=["openai", "gemini", "chatgpt"],
        help="Optional LLM provider (openai, gemini, chatgpt)",
    )
    llm = subparsers.add_parser("llm", help="Manage LLM settings")
    llm_subparsers = llm.add_subparsers(dest="llm_command", required=True)
    llm_set = llm_subparsers.add_parser("set", help="Set LLM configuration values")
    llm_set.add_argument(
        "--provider",
        dest="llm_provider",
        choices=["openai", "gemini", "chatgpt"],
        required=True,
        help="LLM provider (openai, gemini, chatgpt)",
    )
    llm_set.add_argument(
        "--api-key",
        dest="llm_api_key",
        help="LLM API key",
    )
    llm_set.add_argument(
        "--model",
        dest="llm_model",
        help="LLM model name",
    )
    llm_set.add_argument(
        "--base-url",
        dest="llm_base_url",
        help="LLM base URL",
    )
    template = subparsers.add_parser("template", help="Manage note templates")
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
    print("  scan                  Scan for PDFs and generate notes")
    print("  config                Show effective configuration values (default)")
    print("  config show           Show effective configuration values")
    print("  config default        Reset config to defaults")
    print("  config migrate        Migrate config values to the latest schema")
    print("  doctor                Inspect project health")
    print("  init                  Initialize a Zotomatic workspace")
    print("  llm                   Manage LLM settings")
    print("  template create       Create a template and update config")
    print("  template set          Update config to use an existing template")
    print("")
    print("Options:")
    print("  -h, --help            Show this help message and exit")
    print("  -V, --version         Show version and exit")
    print("")
    print("Command options:")
    print("  scan:")
    print("    --once              Scan existing PDFs once and exit")
    print("    --watch             Watch for new PDFs (default)")
    print(
        "    --path PATH [...]   Generate notes for specific PDFs (processed in order) and exit"
    )
    print("    --force             Rescan PDFs and generate missing notes")
    print(
        "    --summary-mode MODE Override summary mode for this scan only (quick, standard, deep)"
    )
    print("  init:")
    print("    --pdf-dir PATH      (required) Directory containing PDF files")
    print("    --note-dir PATH     Override default note directory")
    print("    --template-path PATH  Override default template path")
    print("    --llm-provider      Optional LLM provider (openai, gemini, chatgpt)")
    print("  llm set:")
    print("    --provider          (required) LLM provider (openai, gemini, chatgpt)")
    print("    --api-key           LLM API key")
    print("    --model             LLM model name")
    print("    --base-url          LLM base URL")
    print("  template create/set:")
    print("    --path PATH         (required) Template file path")


def _normalize_cli_options(namespace: argparse.Namespace) -> dict[str, Any]:
    cli_options = {
        key: value
        for key, value in vars(namespace).items()
        if key not in {"command", "template_command", "config_command"}
    }
    provider = cli_options.get("llm_provider")
    if provider == "chatgpt":
        cli_options["llm_provider"] = "openai"
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
        "scan": pipelines.run_scan,
        "doctor": pipelines.run_doctor,
        "init": pipelines.run_init,
        "template": None,
        "config": None,
        "llm": None,
    }

    command = args.command
    cli_options = _normalize_cli_options(args)

    try:
        if command == "template":
            template_command = args.template_command
            if template_command == "create":
                pipelines.run_template_create(cli_options)
            elif template_command == "set":
                pipelines.run_template_set(cli_options)
            else:  # pragma: no cover - argparse enforces choices
                raise ZotomaticCLIError(f"Unknown template command: {template_command}")
            return
        if command == "config":
            config_command = args.config_command
            if not config_command:
                config_command = "show"
            if config_command == "show":
                pipelines.run_config_show(cli_options)
            elif config_command == "default":
                pipelines.run_config_default(cli_options)
            elif config_command == "migrate":
                pipelines.run_config_migrate(cli_options)
            else:  # pragma: no cover - argparse enforces choices
                raise ZotomaticCLIError(f"Unknown config command: {config_command}")
            return
        if command == "llm":
            llm_command = args.llm_command
            if llm_command == "set":
                pipelines.run_llm_set(cli_options)
            else:  # pragma: no cover - argparse enforces choices
                raise ZotomaticCLIError(f"Unknown llm command: {llm_command}")
            return

        handler = handlers[command]
        handler(cli_options)
    except ZotomaticError as exc:
        print(f"zotomatic: error: {exc}", file=sys.stderr)
        hint = getattr(exc, "hint", None)
        if hint:
            print(f"zotomatic: hint: {hint}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
