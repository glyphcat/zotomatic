"""Configuration loading utilities for zotomatic."""

from __future__ import annotations

import os
from dataclasses import dataclass
import re
from pathlib import Path
from typing import Any, Mapping

try:  # Python >=3.11
    import tomllib  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - fallback for <3.11
    tomllib = None  # type: ignore[assignment]

_ENV_PREFIX = "ZOTOMATIC_"
_DEFAULT_CONFIG = Path("~/.zotomatic/config.toml").expanduser()

# TODO: 設定キーの整理
"""
- note_dir: mdファイルの出力先。必要
- pdf_dir: PDFファイルの格納先。ファイル保存の監視先。必要
- pdf_alias_prefix: gitでのコミット管理時に自分が設定したマスクに使う文字列。不要
- llm_provider: 今後の拡張用で、今は使用していない。あってもいい。必須ではない
- llm_openai_model: LLMモデル名。必須？ChatGPTのみに限定するなら必須ではない
- llm_tag_enabled: AI生成のtagを埋め込みするか？必要？ -> LLM利用は有料だったりするため必要とする,
- llm_summary_enabled: AI生成の要約を埋め込みするか？必要？ -> LLM利用は有料だったりするため必要とする,
- llm_openai_api_key: LLMのAPIキー。必須,
- llm_max_input_chars: 14000 必須じゃないが設定値としてはOKとする,
- llm_daily_limit: 1日の利用制限。これはタグ生成とくっつけるべきかもしれない。あった方がいい,
- zotero_api_key: zoteroのAPIキーで必須,
- zotero_library_id: zoteroのライブラリID。ユーザのものを使うなら空文字でOK. 必須ではない,
- zotero_library_scope: "user" or "group". 必須ではない,
- note_title_pattern: 生成されるnoteのタイトル。デフォルトを設けておく。ユーザー設定は必須ではない,

"""

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_DEFAULT_TEMPLATE_PATH = "~/Zotomatic/templates/note.md"


_DEFAULT_SETTINGS: dict[str, Any] = {
    "note_dir": "~/Zotomatic/notes",
    "pdf_dir": "~/Zotero/storage",
    "pdf_alias_prefix": "zotero:/storage",
    "llm_provider": "openai",
    "llm_openai_model": "gpt-4o-mini",
    "llm_openai_base_url": "https://api.openai.com/v1",
    "llm_output_language": "ja",
    "llm_summary_mode": "quick",
    "llm_tag_enabled": True,
    "llm_summary_enabled": True,
    "llm_openai_api_key": "",
    "llm_max_input_chars": 14000,
    "llm_daily_limit": 50,
    "tag_generation_limit": 8,
    "zotero_api_key": "",
    "zotero_library_id": "",
    "zotero_library_scope": "user",
    "note_title_pattern": "{{ year }}-{{ slug80 }}-{{ citekey }}",
    "template_path": _DEFAULT_TEMPLATE_PATH,
}


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


def _build_default_config_template(settings: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# Zotomatic configuration",
            "#",
            "# Update llm_openai_api_key (or export ZOTOMATIC_LLM_OPENAI_API_KEY) before running `zotomatic ready`.",
            "",
            "# Paths & watcher",
            f"note_dir = {_render_value(settings['note_dir'])}",
            f"pdf_dir = {_render_value(settings['pdf_dir'])}",
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
            f"llm_max_input_chars = {_render_value(settings['llm_max_input_chars'])}",
            f"llm_daily_limit = {_render_value(settings['llm_daily_limit'])}",
            "",
            "# Tagging",
            f"tag_generation_limit = {_render_value(settings['tag_generation_limit'])}",
            "",
        ]
    )

# TODO: legacy keyは不要なので削除する
def _coerce_env_value(key: str, value: str) -> Any:
    target_key = key
    default = _DEFAULT_SETTINGS.get(target_key)
    # if default is None and key in _LEGACY_KEY_ALIASES:
    #     target_key = _LEGACY_KEY_ALIASES[key]
    #     default = _DEFAULT_SETTINGS.get(target_key)
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


def _resolve_config_path(cli_options: Mapping[str, Any] | None) -> Path:
    cli_options = dict(cli_options or {})
    raw_config_path = cli_options.get("config_path")
    return Path(raw_config_path).expanduser() if raw_config_path else _DEFAULT_CONFIG


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


def get_config(cli_options: Mapping[str, Any] | None = None) -> dict[str, Any]:
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
    merged.update(file_config)
    merged.update(env_config)
    merged.update(cli_config)

    for key in (
        "pdf_alias_prefix",
        "llm_provider",
        "llm_openai_model",
        "llm_openai_base_url",
    ):
        merged[key] = _DEFAULT_SETTINGS[key]

    merged["config_path"] = str(config_path)
    return merged


@dataclass(slots=True)
class InitResult:
    config_path: Path
    config_created: bool
    config_updated_keys: list[str]
    template_path: Path
    template_created: bool


def initialize_config(cli_options: Mapping[str, Any] | None = None) -> InitResult:
    config_path = _resolve_config_path(cli_options)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    cli_options = dict(cli_options or {})
    init_settings = dict(_DEFAULT_SETTINGS)
    for key, value in cli_options.items():
        if key in init_settings and value is not None:
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
            raise FileNotFoundError(
                f"Default template not found: {source_template}"
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
