"""Configuration loading utilities for zotomatic."""

from __future__ import annotations

import os
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
- notes_output_dir: mdファイルの出力先。必要
- pdf_library_dir: PDFファイルの格納先。ファイル保存の監視先。必要
- pdf_alias_prefix: gitでのコミット管理時に自分が設定したマスクに使う文字列。不要
- llm_provider: 今後の拡張用で、今は使用していない。あってもいい。必須ではない
- llm_model: LLMモデル名。必須？ChatGPTのみに限定するなら必須ではない
- llm_tag_enabled: AI生成のtagを埋め込みするか？必要？ -> LLM利用は有料だったりするため必要とする,
- llm_summary_enabled: AI生成の要約を埋め込みするか？必要？ -> LLM利用は有料だったりするため必要とする,
- llm_api_key: LLMのAPIキー。必須,
- llm_max_input_chars: 14000 必須じゃないが設定値としてはOKとする,
- summary_daily_quota: 1日の利用制限。これはタグ生成とくっつけるべきかもしれない。あった方がいい,
- zotero_api_token: zoteroのAPIキーで必須,
- zotero_library_id: zoteroのライブラリID。ユーザのものを使うなら空文字でOK. 必須ではない,
- zotero_library_scope: "user" or "group". 必須ではない,
- note_title_pattern: 生成されるnoteのタイトル。デフォルトを設けておく。ユーザー設定は必須ではない,

"""

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


_DEFAULT_SETTINGS: dict[str, Any] = {
    "notes_output_dir": "~/Zotomatic/notes",
    "pdf_library_dir": "~/Zotero/storage",
    "pdf_alias_prefix": "zotero:/storage",
    "llm_provider": "openai",
    "llm_model": "gpt-4o-mini",
    "llm_base_url": "https://api.openai.com/v1",
    "llm_output_language": "ja",
    "llm_summary_mode": "quick",
    "llm_tag_enabled": True,
    "llm_summary_enabled": True,
    "llm_api_key": "",
    "llm_max_input_chars": 14000,
    "summary_daily_quota": 50,
    "tag_generation_limit": 8,
    "zotero_api_token": "",
    "zotero_library_id": "",
    "zotero_library_scope": "user",
    "note_title_pattern": "{{ year }}-{{ slug80 }}-{{ citekey }}",
    "note_template_path": str(_TEMPLATES_DIR / "default.md"),
    "heading_summary": "AI-generated Summary",
    "heading_abstract": "Abstract",
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


_DEFAULT_CONFIG_TEMPLATE = "\n".join(
    [
        "# Zotomatic configuration",
        "#",
        "# Update llm_api_key (or export OPENAI_API_KEY / ZOTOMATIC_LLM_API_KEY) before running `zotomatic ready`.",
        "",
        "# Paths & watcher",
        f"notes_output_dir = {_render_value(_DEFAULT_SETTINGS['notes_output_dir'])}",
        f"pdf_library_dir = {_render_value(_DEFAULT_SETTINGS['pdf_library_dir'])}",
        f"pdf_alias_prefix = {_render_value(_DEFAULT_SETTINGS['pdf_alias_prefix'])}",
        "",
        "# Zotero",
        f"zotero_api_token = {_render_value(_DEFAULT_SETTINGS['zotero_api_token'])}",
        f"zotero_library_id = {_render_value(_DEFAULT_SETTINGS['zotero_library_id'])}",
        f"zotero_library_scope = {_render_value(_DEFAULT_SETTINGS['zotero_library_scope'])}",
        "",
        "# Obsidian notes",
        f"note_title_pattern = {_render_value(_DEFAULT_SETTINGS['note_title_pattern'])}",
        "",
        "# AI integration",
        f"llm_provider = {_render_value(_DEFAULT_SETTINGS['llm_provider'])}",
        f"llm_model = {_render_value(_DEFAULT_SETTINGS['llm_model'])}",
        f"llm_api_key = {_render_value(_DEFAULT_SETTINGS['llm_api_key'])}",
        f"llm_summary_enabled = {_render_value(_DEFAULT_SETTINGS['llm_summary_enabled'])}",
        f"llm_tag_enabled = {_render_value(_DEFAULT_SETTINGS['llm_tag_enabled'])}",
        f"llm_summary_mode = {_render_value(_DEFAULT_SETTINGS['llm_summary_mode'])}",
        f"llm_max_input_chars = {_render_value(_DEFAULT_SETTINGS['llm_max_input_chars'])}",
        f"summary_daily_quota = {_render_value(_DEFAULT_SETTINGS['summary_daily_quota'])}",
        "",
        "# Tagging",
        f"tag_generation_limit = {_render_value(_DEFAULT_SETTINGS['tag_generation_limit'])}",
        "",
    ]
)

_ENV_ALIASES = {
    "OPENAI_API_KEY": "llm_api_key",
    "ZOTOMATIC_AI_API_KEY": "llm_api_key",
    "ZOTOMATIC_AI_MODEL": "llm_model",
    "OPENAI_MODEL": "llm_model",
    "OPENAI_MAX_INPUT_CHARS": "llm_max_input_chars",
    "ZOTOMATIC_AI_MAX_INPUT_CHARS": "llm_max_input_chars",
    "OPENAI_MAX_RUNS_PER_DAY": "summary_daily_quota",
    "ZOTOMATIC_AI_MAX_RUNS_PER_DAY": "summary_daily_quota",
    "ZOTERO_API_KEY": "zotero_api_token",
    "ZOTERO_API_TOKEN": "zotero_api_token",
    "ZOTERO_LIBRARY_ID": "zotero_library_id",
    "ZOTERO_LIBRARY_TYPE": "zotero_library_scope",
    "PDF_ROOT": "pdf_library_dir",
    "PDF_ALIAS_ROOT": "pdf_alias_prefix",
    "OUTPUT_DIR": "notes_output_dir",
    "NOTE_TITLE_TEMPLATE": "note_title_pattern",
    "LLM_BASE_URL": "llm_base_url",
    "LLM_OUTPUT_LANGUAGE": "llm_output_language",
}

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
        if env_key in _ENV_ALIASES:
            key = _ENV_ALIASES[env_key]
            config[key] = _coerce_env_value(key, raw_value)
            continue
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

    merged["config_path"] = str(config_path)
    return merged


def initialize_config(cli_options: Mapping[str, Any] | None = None) -> Path:
    config_path = _resolve_config_path(cli_options)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if not config_path.exists():
        config_path.write_text(_DEFAULT_CONFIG_TEMPLATE, encoding="utf-8")
    else:
        existing_content = config_path.read_text(encoding="utf-8")
        missing_keys = [
            key for key in _DEFAULT_SETTINGS if f"{key} =" not in existing_content
        ]
        if missing_keys:
            with config_path.open("a", encoding="utf-8") as handle:
                handle.write(
                    "\n# Added by zotomatic init to ensure required defaults.\n"
                )
                for key in missing_keys:
                    handle.write(f"{key} = {_render_value(_DEFAULT_SETTINGS[key])}\n")

    return config_path.resolve()
