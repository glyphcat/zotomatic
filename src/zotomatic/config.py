"""Configuration loading utilities for zotomatic."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from zotomatic.errors import ZotomaticConfigError
from zotomatic.llm.types import LLM_PROVIDER_DEFAULTS

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

_SCHEMA_VERSION = 2

_DEFAULT_SETTINGS: dict[str, Any] = {
    "note_dir": _default_notes_dir(),
    "pdf_alias_prefix": "zotero:/storage",
    "llm_output_language": "ja",
    "llm_summary_mode": "quick",
    "llm_tag_enabled": True,
    "llm_summary_enabled": True,
    "llm_input_char_limit": 14000,
    "llm_daily_limit": 50,
    "llm_tag_limit": 8,
    "zotero_api_key": "",
    "zotero_library_id": "",
    "zotero_library_scope": "user",
    "note_title_pattern": "{{ year }}-{{ slug80 }}-{{ citekey }}",
    "template_path": _DEFAULT_TEMPLATE_PATH,
    "watch_verbose_logging": False,
}
_INTERNAL_FIXED_SETTINGS = {
    "pdf_alias_prefix",
    "llm_input_char_limit",
    "watch_verbose_logging",
}
_USER_CONFIG_KEYS = {
    "note_dir",
    "pdf_dir",
    "llm_output_language",
    "llm_summary_mode",
    "llm_tag_enabled",
    "llm_summary_enabled",
    "llm_daily_limit",
    "llm_tag_limit",
    "zotero_api_key",
    "zotero_library_id",
    "zotero_library_scope",
    "note_title_pattern",
    "template_path",
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


def user_config_keys() -> set[str]:
    return set(_USER_CONFIG_KEYS)


def _build_default_config_template(settings: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# Zotomatic configuration",
            "#",
            "# LLM settings are optional and can be configured later if needed.",
            f"schema_version = {_render_value(_SCHEMA_VERSION)}",
            "",
            "# Paths & watcher",
            f"note_dir = {_render_value(settings['note_dir'])}",
            'pdf_dir = ""',
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
            f"llm_summary_enabled = {_render_value(settings['llm_summary_enabled'])}",
            f"llm_tag_enabled = {_render_value(settings['llm_tag_enabled'])}",
            f"llm_summary_mode = {_render_value(settings['llm_summary_mode'])}",
            f"llm_input_char_limit = {_render_value(settings['llm_input_char_limit'])}",
            f"llm_daily_limit = {_render_value(settings['llm_daily_limit'])}",
            f"llm_tag_limit = {_render_value(settings['llm_tag_limit'])}",
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


def update_config_section_value(
    config_path: Path,
    section: str,
    key: str,
    value: Any,
) -> bool:
    rendered = f"{key} = {_render_value(value)}"
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(f"[{section}]\n{rendered}\n", encoding="utf-8")
        return True

    text = config_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    section_header = f"[{section}]"
    header_pattern = re.compile(r"^\s*\[(.+)\]\s*$")
    key_pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")

    section_found = False
    in_section = False
    for idx, line in enumerate(lines):
        header_match = header_pattern.match(line)
        if header_match:
            current = header_match.group(1).strip()
            in_section = current == section
            if in_section:
                section_found = True
            continue
        if in_section and key_pattern.match(line):
            if line.strip() == rendered:
                return False
            lines[idx] = rendered
            updated = "\n".join(lines)
            if text.endswith("\n"):
                updated += "\n"
            config_path.write_text(updated, encoding="utf-8")
            return True

    if section_found:
        insert_at = len(lines)
        in_section = False
        for idx, line in enumerate(lines):
            header_match = header_pattern.match(line)
            if header_match:
                current = header_match.group(1).strip()
                if current == section:
                    in_section = True
                    continue
                if in_section:
                    insert_at = idx
                    break
        lines.insert(insert_at, rendered)
        updated = "\n".join(lines)
        if text.endswith("\n"):
            updated += "\n"
        config_path.write_text(updated, encoding="utf-8")
        return True

    if lines and lines[-1].strip():
        lines.append("")
    lines.append(section_header)
    lines.append(rendered)
    updated = "\n".join(lines)
    updated += "\n"
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


def _build_llm_section_from_env(env_config: Mapping[str, Any]) -> dict[str, Any]:
    provider = env_config.get("llm_provider")
    if not provider:
        return {}
    provider_name = str(provider).strip().lower()
    if provider_name == "chatgpt":
        provider_name = "openai"
    if provider_name not in LLM_PROVIDER_DEFAULTS:
        return {}

    providers: dict[str, Any] = {}
    settings: dict[str, Any] = {}
    api_key_key = f"llm_{provider_name}_api_key"
    model_key = f"llm_{provider_name}_model"
    base_url_key = f"llm_{provider_name}_base_url"
    if api_key := env_config.get(api_key_key):
        settings["api_key"] = api_key
    if model := env_config.get(model_key):
        settings["model"] = model
    if base_url := env_config.get(base_url_key):
        settings["base_url"] = base_url
    providers[provider_name] = settings
    return {"provider": provider_name, "providers": providers}


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
    llm_env_section = _build_llm_section_from_env(env_config)
    if llm_env_section:
        if isinstance(merged.get("llm"), Mapping):
            merged_llm = dict(merged["llm"])
            if "provider" in llm_env_section:
                merged_llm["provider"] = llm_env_section["provider"]
            providers = merged_llm.get("providers")
            if not isinstance(providers, Mapping):
                providers = {}
            else:
                providers = dict(providers)
            env_providers = llm_env_section.get("providers", {})
            if isinstance(env_providers, Mapping):
                for provider, env_settings in env_providers.items():
                    if not isinstance(env_settings, Mapping):
                        continue
                    settings = dict(providers.get(provider, {}))
                    settings.update(env_settings)
                    providers[provider] = settings
            merged_llm["providers"] = providers
            merged["llm"] = merged_llm
        else:
            merged["llm"] = llm_env_section
        sources["llm"] = "env"
    for key, value in cli_config.items():
        merged[key] = value
        sources[key] = "cli"

    for key in _INTERNAL_FIXED_SETTINGS:
        merged[key] = _DEFAULT_SETTINGS[key]
        sources[key] = "fixed"

    merged["config_path"] = str(config_path)
    sources["config_path"] = "fixed"
    for key in _USER_CONFIG_KEYS:
        if key not in merged:
            merged[key] = None
            sources[key] = "unset"
    if merged.get("pdf_dir") in {"", None}:
        merged["pdf_dir"] = None
        sources["pdf_dir"] = "unset"
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


@dataclass(slots=True)
class MigrationResult:
    config_path: Path
    backup_path: Path | None
    updated_keys: list[str]
    removed_keys: list[str]


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


def migrate_config(config_path: Path | None = None) -> MigrationResult:
    config_path = config_path or _DEFAULT_CONFIG
    if not config_path.exists():
        raise ZotomaticConfigError(
            f"Config not found: {config_path}",
            hint="Run `zotomatic init` first to create a config file.",
        )
    if tomllib is None:
        raise ZotomaticConfigError(
            "TOML parser is not available.",
            hint="Use Python 3.11+ or install tomli for older versions.",
        )

    original_text = config_path.read_text(encoding="utf-8")
    try:
        data = tomllib.loads(original_text)  # type: ignore[union-attr]
    except (OSError, ValueError) as exc:
        raise ZotomaticConfigError(
            "Failed to parse config file.",
            hint="Fix the TOML syntax and retry.",
        ) from exc

    updated_keys: list[str] = []
    removed_keys: list[str] = []
    backup_path: Path | None = None

    def _ensure_backup() -> None:
        nonlocal backup_path
        if backup_path is not None:
            return
        backup_path = config_path.with_name(config_path.name + ".bak")
        if not backup_path.exists():
            backup_path.write_text(original_text, encoding="utf-8")

    def _parse_schema_version(config_data: Mapping[str, Any]) -> int:
        raw_version = config_data.get("schema_version", 0)
        try:
            return int(raw_version)
        except (TypeError, ValueError):
            return 0

    def _remove_top_level_keys(keys: set[str]) -> bool:
        nonlocal removed_keys
        text = config_path.read_text(encoding="utf-8")
        legacy_pattern = re.compile(
            rf"^\s*({'|'.join(re.escape(key) for key in keys)})\s*="
        )
        cleaned_lines: list[str] = []
        removed = False
        for line in text.splitlines():
            if legacy_pattern.match(line):
                removed = True
                removed_keys.append(line.split("=", 1)[0].strip())
                continue
            cleaned_lines.append(line)
        if removed:
            _ensure_backup()
            updated_text = "\n".join(cleaned_lines)
            if text.endswith("\n"):
                updated_text += "\n"
            config_path.write_text(updated_text, encoding="utf-8")
        return removed

    def _migration_openai_legacy(config_data: Mapping[str, Any]) -> None:
        legacy_keys = {
            "llm_openai_api_key",
            "llm_openai_model",
            "llm_openai_base_url",
        }
        legacy_values = {
            key: config_data.get(key) for key in legacy_keys if key in config_data
        }
        if not legacy_values:
            return

        llm_section = (
            config_data.get("llm")
            if isinstance(config_data.get("llm"), Mapping)
            else {}
        )
        provider = str(llm_section.get("provider") or "").strip().lower()
        if not provider:
            provider = "openai"
            if update_config_section_value(
                config_path, "llm", "provider", provider
            ):
                updated_keys.append("llm.provider")

        providers = (
            llm_section.get("providers") if isinstance(llm_section, Mapping) else {}
        )
        provider_settings = (
            providers.get(provider) if isinstance(providers, Mapping) else {}
        )
        if not isinstance(provider_settings, Mapping):
            provider_settings = {}

        defaults = LLM_PROVIDER_DEFAULTS.get("openai", {})
        legacy_api_key = str(legacy_values.get("llm_openai_api_key") or "").strip()
        legacy_model = str(legacy_values.get("llm_openai_model") or "").strip()
        legacy_base_url = str(legacy_values.get("llm_openai_base_url") or "").strip()

        api_key = str(provider_settings.get("api_key") or "").strip()
        if not api_key and legacy_api_key:
            if update_config_section_value(
                config_path,
                "llm.providers.openai",
                "api_key",
                legacy_api_key,
            ):
                updated_keys.append("llm.providers.openai.api_key")

        model = str(provider_settings.get("model") or "").strip()
        if not model:
            model_value = legacy_model or defaults.get("model")
            if model_value and update_config_section_value(
                config_path,
                "llm.providers.openai",
                "model",
                model_value,
            ):
                updated_keys.append("llm.providers.openai.model")

        base_url = str(provider_settings.get("base_url") or "").strip()
        if not base_url:
            base_url_value = legacy_base_url or defaults.get("base_url")
            if base_url_value and update_config_section_value(
                config_path,
                "llm.providers.openai",
                "base_url",
                base_url_value,
            ):
                updated_keys.append("llm.providers.openai.base_url")

        _remove_top_level_keys(legacy_keys)

    def _migration_tag_limit(config_data: Mapping[str, Any]) -> None:
        legacy_key = "tag_generation_limit"
        if legacy_key not in config_data:
            return
        legacy_value = config_data.get(legacy_key)
        if "llm_tag_limit" not in config_data:
            if update_config_value(config_path, "llm_tag_limit", legacy_value):
                updated_keys.append("llm_tag_limit")
        _remove_top_level_keys({legacy_key})

    current_version = _parse_schema_version(data)
    if current_version >= _SCHEMA_VERSION:
        return MigrationResult(
            config_path=config_path.resolve(),
            backup_path=None,
            updated_keys=updated_keys,
            removed_keys=removed_keys,
        )

    _ensure_backup()

    migrations = [
        (0, 1, _migration_openai_legacy),
        (1, 2, _migration_tag_limit),
    ]

    for from_version, to_version, handler in migrations:
        if current_version != from_version:
            continue
        handler(data)
        if update_config_value(config_path, "schema_version", to_version):
            updated_keys.append("schema_version")
        current_version = to_version
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))  # type: ignore[union-attr]

    return MigrationResult(
        config_path=config_path.resolve(),
        backup_path=backup_path.resolve() if backup_path else None,
        updated_keys=updated_keys,
        removed_keys=removed_keys,
    )
