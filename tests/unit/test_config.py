from __future__ import annotations

from pathlib import Path

import pytest

from zotomatic import config


def test_update_config_value_creates_and_updates(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    created = config.update_config_value(cfg, "note_dir", "/tmp/notes")
    assert created is True
    assert "note_dir" in cfg.read_text(encoding="utf-8")

    updated = config.update_config_value(cfg, "note_dir", "/tmp/notes")
    assert updated is False

    updated = config.update_config_value(cfg, "note_dir", "/tmp/notes2")
    assert updated is True
    assert "/tmp/notes2" in cfg.read_text(encoding="utf-8")


def test_update_config_section_value_creates_and_updates(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    created = config.update_config_section_value(
        cfg, "llm.providers.openai", "api_key", "key"
    )
    assert created is True
    text = cfg.read_text(encoding="utf-8")
    assert "[llm.providers.openai]" in text
    assert "api_key = \"key\"" in text

    updated = config.update_config_section_value(
        cfg, "llm.providers.openai", "api_key", "key"
    )
    assert updated is False

    updated = config.update_config_section_value(
        cfg, "llm.providers.openai", "api_key", "key2"
    )
    assert updated is True
    assert "api_key = \"key2\"" in cfg.read_text(encoding="utf-8")


def test_initialize_config_creates_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    source_template = templates_dir / "note.md"
    source_template.write_text("Template", encoding="utf-8")
    monkeypatch.setattr(config, "_TEMPLATES_DIR", templates_dir)

    cfg_path = tmp_path / "config.toml"
    monkeypatch.setattr(config, "_DEFAULT_CONFIG", cfg_path)
    template_target = tmp_path / "note.md"
    result = config.initialize_config(
        {
            "template_path": str(template_target),
            "note_dir": str(tmp_path / "notes"),
            "pdf_dir": str(tmp_path / "pdfs"),
            "note_title_pattern": "{{ title }}",
        }
    )
    assert result.config_created is True
    assert result.template_created is True
    assert cfg_path.exists()
    assert template_target.exists()


def test_get_config_merges_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text("note_dir = \"/file\"\n", encoding="utf-8")
    monkeypatch.setattr(config, "_DEFAULT_CONFIG", cfg_path)
    monkeypatch.setenv("ZOTOMATIC_NOTE_DIR", "/env")

    merged = config.get_config({"note_dir": "/cli"})
    assert merged["note_dir"] == "/cli"
    assert merged["config_path"] == str(cfg_path)


def test_default_config_path_is_path() -> None:
    path = config._default_config_path()
    assert isinstance(path, Path)


def test_default_paths_are_absolute() -> None:
    note_dir = Path(config._DEFAULT_SETTINGS["note_dir"])
    template_path = Path(config._DEFAULT_SETTINGS["template_path"])
    assert note_dir.is_absolute()
    assert template_path.is_absolute()


def test_reset_config_to_defaults_creates_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    source_template = templates_dir / "note.md"
    source_template.write_text("Template", encoding="utf-8")
    monkeypatch.setattr(config, "_TEMPLATES_DIR", templates_dir)

    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text("note_dir = \"/custom\"\n", encoding="utf-8")
    template_target = tmp_path / "note.md"

    monkeypatch.setattr(config, "_DEFAULT_CONFIG", cfg_path)
    monkeypatch.setitem(
        config._DEFAULT_SETTINGS, "template_path", str(template_target)
    )

    result = config.reset_config_to_defaults()
    assert result.config_path == cfg_path
    assert result.backup_path == cfg_path.with_name("config.toml.bak")
    backup_path = result.backup_path
    assert backup_path is not None
    assert backup_path.exists()
    assert "note_dir" in cfg_path.read_text(encoding="utf-8")
    assert result.template_path == template_target
    assert template_target.exists()


def test_migrate_config_updates_llm_schema(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(
        "\n".join(
            [
                "note_dir = \"/notes\"",
                "llm_openai_api_key = \"key\"",
                "llm_openai_model = \"model-x\"",
                "llm_openai_base_url = \"https://example.com\"",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = config.migrate_config(cfg_path)
    assert result.updated_keys
    assert result.removed_keys
    backup_path = result.backup_path
    assert backup_path is not None
    assert backup_path.exists()
    text = cfg_path.read_text(encoding="utf-8")
    assert "llm_openai_api_key" not in text
    assert "schema_version = 2" in text
    assert "[llm]" in text
    assert "provider = \"openai\"" in text
    assert "[llm.providers.openai]" in text
    assert "api_key = \"key\"" in text
    assert "model = \"model-x\"" in text
    assert "base_url = \"https://example.com\"" in text


def test_migrate_config_no_changes(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text("note_dir = \"/notes\"\n", encoding="utf-8")
    result = config.migrate_config(cfg_path)
    assert "schema_version" in result.updated_keys
    assert result.removed_keys == []
    text = cfg_path.read_text(encoding="utf-8")
    assert "schema_version" in text


def test_migrate_config_tag_limit(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(
        "\n".join(
            [
                "note_dir = \"/notes\"",
                "schema_version = 1",
                "tag_generation_limit = 5",
                "",
            ]
        ),
        encoding="utf-8",
    )
    result = config.migrate_config(cfg_path)
    assert "llm_tag_limit" in result.updated_keys
    text = cfg_path.read_text(encoding="utf-8")
    assert "tag_generation_limit" not in text
    assert "llm_tag_limit = 5" in text


def test_build_llm_section_from_env() -> None:
    env = {
        "llm_provider": "gemini",
        "llm_gemini_api_key": "key",
        "llm_gemini_model": "model",
    }
    section = config._build_llm_section_from_env(env)
    assert section["provider"] == "gemini"
    providers = section["providers"]
    assert providers["gemini"]["api_key"] == "key"
    assert providers["gemini"]["model"] == "model"
