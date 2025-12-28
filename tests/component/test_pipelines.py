from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from zotomatic import pipelines
from zotomatic.repositories.types import WatcherStateRepositoryConfig


def test_run_template_create(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config_path = tmp_path / "config.toml"
    template_path = tmp_path / "note.md"

    pipelines.run_template_create(
        {"template_path": str(template_path), "config_path": str(config_path)}
    )

    assert template_path.exists()
    text = config_path.read_text(encoding="utf-8")
    assert "template_path" in text

    captured = capsys.readouterr()
    assert "Template" in captured.out


def test_run_template_set(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    template_path = tmp_path / "note.md"
    template_path.write_text("x", encoding="utf-8")

    pipelines.run_template_set(
        {"template_path": str(template_path), "config_path": str(config_path)}
    )

    text = config_path.read_text(encoding="utf-8")
    assert "template_path" in text


def test_run_doctor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pdf_dir = tmp_path / "pdfs"
    note_dir = tmp_path / "notes"
    template_path = tmp_path / "note.md"
    pdf_dir.mkdir()
    template_path.write_text("x", encoding="utf-8")

    settings = {
        "config_path": str(tmp_path / "config.toml"),
        "pdf_dir": str(pdf_dir),
        "note_dir": str(note_dir),
        "template_path": str(template_path),
        "llm_openai_api_key": "",
        "zotero_api_key": "",
        "zotero_library_id": "",
        "zotero_library_scope": "user",
    }
    config_path = Path(settings["config_path"])
    config_path.write_text("", encoding="utf-8")

    class DummyResult:
        stdout = ""

    monkeypatch.setattr(pipelines.config, "get_config", lambda _opts: settings)
    monkeypatch.setattr(pipelines.subprocess, "run", lambda *args, **kwargs: DummyResult())

    result = pipelines.run_doctor({})
    assert result == 0


def test_run_init(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    config_path = tmp_path / "config.toml"
    template_path = tmp_path / "note.md"
    db_path = tmp_path / "state.db"

    monkeypatch.setattr(
        pipelines.WatcherStateRepositoryConfig,
        "from_settings",
        lambda _settings: WatcherStateRepositoryConfig(sqlite_path=db_path),
    )
    monkeypatch.setattr(pipelines.WatcherStateRepository, "from_settings", lambda _settings: object())

    pipelines.run_init(
        {
            "pdf_dir": str(tmp_path / "pdfs"),
            "note_dir": str(tmp_path / "notes"),
            "template_path": str(template_path),
            "config_path": str(config_path),
        }
    )

    captured = capsys.readouterr()
    assert "Config:" in captured.out
    assert "Template:" in captured.out
    assert "DB:" in captured.out
