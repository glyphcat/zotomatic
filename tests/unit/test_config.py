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


def test_initialize_config_creates_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    source_template = templates_dir / "note.md"
    source_template.write_text("Template", encoding="utf-8")
    monkeypatch.setattr(config, "_TEMPLATES_DIR", templates_dir)

    cfg_path = tmp_path / "config.toml"
    template_target = tmp_path / "note.md"
    result = config.initialize_config(
        {
            "config_path": str(cfg_path),
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
    monkeypatch.setenv("ZOTOMATIC_NOTE_DIR", "/env")
    monkeypatch.setenv("ZOTOMATIC_LLM_OPENAI_BASE_URL", "http://example.com")

    merged = config.get_config({"config_path": str(cfg_path), "note_dir": "/cli"})
    assert merged["note_dir"] == "/cli"
    assert merged["llm_openai_base_url"] == config._DEFAULT_SETTINGS["llm_openai_base_url"]
    assert merged["config_path"] == str(cfg_path)


def test_default_config_path_is_path() -> None:
    path = config._default_config_path()
    assert isinstance(path, Path)
