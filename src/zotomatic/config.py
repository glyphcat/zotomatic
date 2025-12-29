"""Configuration loading utilities for zotomatic."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from zotomatic.errors import ZotomaticConfigError
try:  # Python >=3.11
    import tomllib  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - fallback for <3.11
    tomllib = None  # type: ignore[assignment]

_ENV_PREFIX = "ZOTOMATIC_"
_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def _default_config_path() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base) / "Zotomatic" / "config.toml"
        return Path.home() / "AppData" / "Local" / "Zotomatic" / "config.toml"
    return Path("~/.zotomatic/config.toml").expanduser()


def _default_notes_dir() -> str:
    return str(Path.home() / "Zotomatic" / "notes")


def _default_template_path() -> str:
    return str(Path.home() / "Zotomatic" / "templates" / "note.md")


_DEFAULT_CONFIG = _default_config_path()
_DEFAULT_TEMPLATE_PATH = _default_template_path()


_DEFAULT_SETTINGS: dict[str, Any] = {
    "note_dir": _default_notes_dir(),
    "pdf_alias_prefix": "zotero:/storage",
    "llm_provider": "openai",
    "llm_openai_model": "gpt-4o-mini",
    "llm_openai_base_url": "https://api.openai.com/v1",
    "llm_output_language": "ja",
    "llm_summary_mode": "quick",
    "llm_tag_enabled": True,
    "llm_summary_enabled": True,
    "llm_openai_api_key": "",
    "llm_input_char_limit": 14000,
    "llm_daily_limit": 50,
    "tag_generation_limit": 8,
    "zotero_api_key": "",
    "zotero_library_id": "",
    "zotero_library_scope": "user",
    "note_title_pattern": "{{ year }}-{{ slug80 }}-{{ citekey }}",
    "template_path": _DEFAULT_TEMPLATE_PATH,
    "watch_verbose_logging": False,
}
_INTERNAL_FIXED_SETTINGS = {
    "pdf_alias_prefix",
    "llm_provider",
    "llm_openai_model",
    "llm_openai_base_url",
    "llm_input_char_limit",
    "watch_verbose_logging",
}
_CONFIG_SHOW_EXCLUDE_SETTINGS = _INTERNAL_FIXED_SETTINGS | {"config_path"}


def _render_value(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str) and "\n" in value:
        escaped = value.replace('"""', '"""')
        return f'"""{escaped}"""'
    escaped = str(value).replace('"', '"')
    return f'"{escaped}"'


def render_value(value: Any) -> str:
    return _render_value(value)


def config_show_exclusions() -> set[str]:
    return set(_CONFIG_SHOW_EXCLUDE_SETTINGS)


def _build_default_config_template(settings: Mapping[str, Any]) -> str:
    pdf_dir = settings.get("pdf_dir")
    pdf_dir_line = f"pdf_dir = {_render_value(pdf_dir)}" if pdf_dir else None
    return "\n".join(
        [
            "# Zotomatic configuration",
            "#",
            "# Update llm_openai_api_key (or export ZOTOMATIC_LLM_OPENAI_API_KEY) before running `zotomatic scan`.",
            "",
            "# Paths & watcher",
            f"note_dir = {_render_value(settings['note_dir'])}",
            *(line for line in [pdf_dir_line] if line),
            "",
            "# Zotero",
            f"zotero_api_key = {_render_value(settings['zotero_api_key'])}",
            f"zotero_library_id = {_render_value(settings['zotero_library_id'])}",
            f"zotero_library_scope = {_render_value(settings['zotero_library_scope'])}",
            "",
            "# Obsidian notes",
            f"note_title_pattern = {_render_value(settings['note_title_pattern'])}",
            f"template_path = {_render_value(settings['template_path'])}",
            "",
            "# AI integration",
            f"llm_openai_api_key = {_render_value(settings['llm_openai_api_key'])}",
            f"llm_summary_enabled = {_render_value(settings['llm_summary_enabled'])}",
            f"llm_tag_enabled = {_render_value(settings['llm_tag_enabled'])}",
            f"llm_summary_mode = {_render_value(settings['llm_summary_mode'])}",
            f"llm_input_char_limit = {_render_value(settings['llm_input_char_limit'])}",
            f"llm_daily_limit = {_render_value(settings['llm_daily_limit'])}",
            "",
            "# Tagging",
            f"tag_generation_limit = {_render_value(settings['tag_generation_limit'])}",
            "",
        ]
    )


def _coerce_env_value(key: str, value: str) -> Any:
    target_key = key
    default = _DEFAULT_SETTINGS.get(target_key)
    if isinstance(default, bool):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(default, int):
        try:
            return int(value)
        except ValueError:
            return default
    if isinstance(default, float):
        try:
            return float(value)
        except ValueError:
            return default
    return value


def _resolve_config_path(_cli_options: Mapping[str, Any] | None) -> Path:
    return _DEFAULT_CONFIG


def update_config_value(config_path: Path, key: str, value: Any) -> bool:
    rendered = f"{key} = {_render_value(value)}"
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(rendered + "\n", encoding="utf-8")
        return True

    text = config_path.read_text(encoding="utf-8")
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if pattern.match(line):
            if line.strip() == rendered:
                return False
            lines[idx] = rendered
            updated = "\n".join(lines)
            if text.endswith("\n"):
                updated += "\n"
            config_path.write_text(updated, encoding="utf-8")
            return True

    updated = text.rstrip("\n") + "\n" + rendered + "\n"
    config_path.write_text(updated, encoding="utf-8")
    return True


def _load_file_config(path: Path) -> dict[str, Any]:
    if tomllib is None or not path.is_file():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))  # type: ignore[union-attr]
    except (OSError, ValueError):
        return {}


def _load_env_config() -> dict[str, Any]:
    config: dict[str, Any] = {}
    for env_key, raw_value in os.environ.items():
        if env_key.startswith(_ENV_PREFIX):
            normalized = env_key[len(_ENV_PREFIX) :].lower()
            config[normalized] = _coerce_env_value(normalized, raw_value)
    return config


def get_config_with_sources(
    cli_options: Mapping[str, Any] | None = None,
) -> dict[str, tuple[Any, str]]:
    cli_options = dict(cli_options or {})
    config_path = _resolve_config_path(cli_options)

    file_config = _load_file_config(config_path)
    env_config = _load_env_config()
    cli_config = {
        key: value
        for key, value in cli_options.items()
        if value is not None and key != "config_path"
    }

    merged: dict[str, Any] = dict(_DEFAULT_SETTINGS)
    sources: dict[str, str] = {key: "default" for key in merged}
    for key, value in file_config.items():
        merged[key] = value
        sources[key] = "file"
    for key, value in env_config.items():
        merged[key] = value
        sources[key] = "env"
    for key, value in cli_config.items():
        merged[key] = value
        sources[key] = "cli"

    for key in _INTERNAL_FIXED_SETTINGS:
        merged[key] = _DEFAULT_SETTINGS[key]
        sources[key] = "fixed"

    merged["config_path"] = str(config_path)
    sources["config_path"] = "fixed"
    return {key: (merged[key], sources.get(key, "default")) for key in merged}


def get_config(cli_options: Mapping[str, Any] | None = None) -> dict[str, Any]:
    merged = get_config_with_sources(cli_options)
    return {key: value for key, (value, _source) in merged.items()}


@dataclass(slots=True)
class InitResult:
    config_path: Path
    config_created: bool
    config_updated_keys: list[str]
    template_path: Path
    template_created: bool


@dataclass(slots=True)
class ResetResult:
    config_path: Path
    backup_path: Path | None
    template_path: Path
    template_created: bool


def initialize_config(cli_options: Mapping[str, Any] | None = None) -> InitResult:
    config_path = _resolve_config_path(cli_options)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    cli_options = dict(cli_options or {})
    init_settings = dict(_DEFAULT_SETTINGS)
    for key, value in cli_options.items():
        if value is None or key == "config_path":
            continue
        if key in init_settings or key == "pdf_dir":
            init_settings[key] = value

    config_created = False
    config_updated_keys: list[str] = []
    if not config_path.exists():
        config_path.write_text(
            _build_default_config_template(init_settings), encoding="utf-8"
        )
        config_created = True
    else:
        existing_content = config_path.read_text(encoding="utf-8")
        missing_keys = [
            key for key in _DEFAULT_SETTINGS if f"{key} =" not in existing_content
        ]
        if missing_keys:
            config_updated_keys = list(missing_keys)
            with config_path.open("a", encoding="utf-8") as handle:
                handle.write(
                    "\n# Added by zotomatic init to ensure required defaults.\n"
                )
                for key in missing_keys:
                    handle.write(f"{key} = {_render_value(init_settings[key])}\n")

    template_path_value = init_settings["template_path"]
    try:
        file_config = _load_file_config(config_path)
        if "template_path" not in cli_options and file_config.get("template_path"):
            template_path_value = file_config["template_path"]
    except OSError:
        template_path_value = init_settings["template_path"]

    template_path = Path(str(template_path_value)).expanduser()
    template_created = False
    if not template_path.exists():
        template_path.parent.mkdir(parents=True, exist_ok=True)
        source_template = _TEMPLATES_DIR / "note.md"
        if not source_template.is_file():
            raise ZotomaticConfigError(
                f"Default template not found: {source_template}",
                hint="Reinstall Zotomatic or restore the default template file.",
            )
        template_path.write_text(
            source_template.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        template_created = True

    return InitResult(
        config_path=config_path.resolve(),
        config_created=config_created,
        config_updated_keys=config_updated_keys,
        template_path=template_path.resolve(),
        template_created=template_created,
    )


def reset_config_to_defaults() -> ResetResult:
    config_path = _DEFAULT_CONFIG
    config_path.parent.mkdir(parents=True, exist_ok=True)

    backup_path: Path | None = None
    if config_path.exists():
        backup_path = config_path.with_name(config_path.name + ".bak")
        backup_path.write_text(
            config_path.read_text(encoding="utf-8"), encoding="utf-8"
        )

    config_path.write_text(
        _build_default_config_template(_DEFAULT_SETTINGS), encoding="utf-8"
    )

    template_path = Path(str(_DEFAULT_SETTINGS["template_path"])).expanduser()
    template_created = False
    if not template_path.exists():
        template_path.parent.mkdir(parents=True, exist_ok=True)
        source_template = _TEMPLATES_DIR / "note.md"
        if not source_template.is_file():
            raise ZotomaticConfigError(
                f"Default template not found: {source_template}",
                hint="Reinstall Zotomatic or restore the default template file.",
            )
        template_path.write_text(
            source_template.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        template_created = True

    return ResetResult(
        config_path=config_path.resolve(),
        backup_path=backup_path.resolve() if backup_path else None,
        template_path=template_path.resolve(),
        template_created=template_created,
    )
