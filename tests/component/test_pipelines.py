from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from zotomatic import pipelines
from zotomatic.errors import ZotomaticCLIError
from zotomatic.repositories.types import WatcherStateRepositoryConfig


def test_run_template_create(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config_path = tmp_path / "config.toml"
    template_path = tmp_path / "note.md"

    monkeypatch.setattr(pipelines.config, "_DEFAULT_CONFIG", config_path)

    pipelines.run_template_create(
        {"template_path": str(template_path)}
    )

    assert template_path.exists()
    text = config_path.read_text(encoding="utf-8")
    assert "template_path" in text

    captured = capsys.readouterr()
    assert "Template" in captured.out


def test_run_template_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "config.toml"
    template_path = tmp_path / "note.md"
    template_path.write_text("x", encoding="utf-8")

    monkeypatch.setattr(pipelines.config, "_DEFAULT_CONFIG", config_path)

    pipelines.run_template_set(
        {"template_path": str(template_path)}
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
    monkeypatch.setattr(pipelines.config, "_DEFAULT_CONFIG", config_path)

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
        }
    )

    captured = capsys.readouterr()
    assert "Config:" in captured.out
    assert "Template:" in captured.out
    assert "DB:" in captured.out


def test_run_scan_path_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_text("dummy", encoding="utf-8")
    template_path = tmp_path / "note.md"
    template_path.write_text("{title}", encoding="utf-8")
    note_dir = tmp_path / "notes"

    settings = {
        "note_dir": str(note_dir),
        "template_path": str(template_path),
        "note_title_pattern": "note-{{ title }}",
        "llm_openai_api_key": "",
        "zotero_api_key": "",
        "zotero_library_id": "",
        "zotero_library_scope": "user",
    }

    class DummyUsageStore:
        def get(self, _usage_date: str):
            return None

        def upsert(self, _entry) -> None:
            return None

    class DummyUsageRepo:
        usage = DummyUsageStore()

    monkeypatch.setattr(pipelines.config, "get_config", lambda _opts: settings)
    monkeypatch.setattr(
        pipelines.LLMUsageRepository,
        "from_settings",
        lambda _settings: DummyUsageRepo(),
    )

    result = pipelines.run_scan({"path": [str(pdf_path)]})
    assert result == 0

    notes = list(note_dir.rglob("*.md"))
    assert len(notes) == 1

    captured = capsys.readouterr()
    assert "Scan started (path)." in captured.out
    assert "Scan completed (path)." in captured.out
    assert "Summary: created=" in captured.out
    assert "pending=0" in captured.out
    assert "dropped=0" in captured.out
    assert "pending=0" in captured.out
    assert "dropped=0" in captured.out
    assert "Note created:" in captured.out


def test_run_scan_watch_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    settings = {
        "note_dir": str(tmp_path / "notes"),
        "template_path": str(tmp_path / "note.md"),
        "note_title_pattern": "note-{{ title }}",
        "llm_openai_api_key": "",
        "zotero_api_key": "",
        "zotero_library_id": "",
        "zotero_library_scope": "user",
        "pdf_dir": str(tmp_path / "pdfs"),
    }
    Path(settings["note_dir"]).mkdir(parents=True, exist_ok=True)
    Path(settings["template_path"]).write_text("{title}", encoding="utf-8")
    Path(settings["pdf_dir"]).mkdir(parents=True, exist_ok=True)

    class DummyUsageStore:
        def get(self, _usage_date: str):
            return None

        def upsert(self, _entry) -> None:
            return None

    class DummyUsageRepo:
        usage = DummyUsageStore()

    monkeypatch.setattr(pipelines.config, "get_config", lambda _opts: settings)
    monkeypatch.setattr(
        pipelines.LLMUsageRepository,
        "from_settings",
        lambda _settings: DummyUsageRepo(),
    )

    class DummyMeta:
        def get(self, _key: str):
            return None

        def set(self, _key: str, _value: str) -> None:
            return None

    class DummyStateRepo:
        meta = DummyMeta()
        pending = object()
        zotero_attachment = object()
        file_state = None
        directory_state = None

    class DummyPendingQueue:
        def enqueue(self, _path):
            return None

        def get_due(self, limit=1):
            return []

        def count_all(self):
            return 0

        def list_all(self, limit=10):
            return []

    class DummyWatcher:
        def __init__(self, _config):
            self.skipped_by_state = 0
            self._config = _config

        def __enter__(self):
            if self._config.on_initial_scan_complete:
                self._config.on_initial_scan_complete()
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

    class DummyPendingProcessor:
        loop_interval_seconds = 0
        skipped_unreadable = 0
        dropped_count = 0
        dropped_paths = []
        call_count = 0

        def run_once(self):
            self.call_count += 1
            return 0

    monkeypatch.setattr(pipelines, "PDFStorageWatcher", DummyWatcher)
    dummy_processor = DummyPendingProcessor()
    monkeypatch.setattr(
        pipelines, "PendingQueueProcessor", lambda *args, **kwargs: dummy_processor
    )
    monkeypatch.setattr(
        pipelines.PendingQueue, "from_state_repository", lambda _state: DummyPendingQueue()
    )
    monkeypatch.setattr(
        pipelines.WatcherStateRepository, "from_settings", lambda _settings: DummyStateRepo()
    )
    monkeypatch.setattr(
        pipelines.ZoteroResolver,
        "from_state_repository",
        lambda *args, **kwargs: object(),
    )

    class DummyEvent:
        def set(self):
            return None

        def wait(self, _timeout):
            return True

        def is_set(self):
            return False

    dummy_event = DummyEvent()
    monkeypatch.setattr(pipelines.threading, "Event", lambda: dummy_event)

    pipelines.run_scan({"watch": True})
    captured = capsys.readouterr()
    assert (
        "Initial scan complete. Processing queued PDFs... (press Ctrl+C to stop)"
        in captured.out
    )
    assert "Initial processing complete." in captured.out
    assert "Waiting for new PDFs..." in captured.out
    assert dummy_processor.call_count >= 1


def test_run_scan_path_invalid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    template_path = tmp_path / "note.md"
    template_path.write_text("{title}", encoding="utf-8")
    note_dir = tmp_path / "notes"

    settings = {
        "note_dir": str(note_dir),
        "template_path": str(template_path),
        "note_title_pattern": "note-{{ title }}",
        "llm_openai_api_key": "",
        "zotero_api_key": "",
        "zotero_library_id": "",
        "zotero_library_scope": "user",
    }

    class DummyUsageStore:
        def get(self, _usage_date: str):
            return None

        def upsert(self, _entry) -> None:
            return None

    class DummyUsageRepo:
        usage = DummyUsageStore()

    missing = tmp_path / "missing.pdf"
    monkeypatch.setattr(pipelines.config, "get_config", lambda _opts: settings)
    monkeypatch.setattr(
        pipelines.LLMUsageRepository,
        "from_settings",
        lambda _settings: DummyUsageRepo(),
    )

    with pytest.raises(ZotomaticCLIError) as excinfo:
        pipelines.run_scan({"path": [str(missing)]})
    assert "Invalid PDF path(s)" in str(excinfo.value)


def test_run_scan_force_with_path_rejected() -> None:
    with pytest.raises(ZotomaticCLIError) as excinfo:
        pipelines.run_scan({"path": ["/tmp/a.pdf"], "force": True})
    assert "--force cannot be used with --path" in str(excinfo.value)


def test_run_config_show_filters_internal_keys(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    settings = {
        "note_dir": ("/notes", "default"),
        "pdf_dir": (None, "unset"),
        "llm_openai_model": ("ignored", "fixed"),
        "config_path": ("/fixed/config.toml", "fixed"),
        "watch_verbose_logging": (True, "fixed"),
    }

    monkeypatch.setattr(
        pipelines.config, "get_config_with_sources", lambda _opts: settings
    )
    monkeypatch.setattr(
        pipelines.config,
        "user_config_keys",
        lambda: {"note_dir", "pdf_dir"},
    )

    result = pipelines.run_config_show({})
    assert result == 0
    captured = capsys.readouterr()
    assert "note_dir =" in captured.out
    assert "(default)" in captured.out
    assert "pdf_dir" in captured.out
    assert "(unset)" in captured.out


def test_run_config_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    source_template = templates_dir / "note.md"
    source_template.write_text("Template", encoding="utf-8")

    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text("note_dir = \"/custom\"\n", encoding="utf-8")
    template_target = tmp_path / "note.md"

    monkeypatch.setattr(pipelines.config, "_TEMPLATES_DIR", templates_dir)
    monkeypatch.setattr(pipelines.config, "_DEFAULT_CONFIG", cfg_path)
    monkeypatch.setitem(
        pipelines.config._DEFAULT_SETTINGS, "template_path", str(template_target)
    )

    result = pipelines.run_config_default({})
    assert result == 0
    captured = capsys.readouterr()
    assert "Config: reset to defaults" in captured.out
    assert "Config: backup created" in captured.out
    assert "Template:" in captured.out
    assert cfg_path.exists()
    assert cfg_path.with_name("config.toml.bak").exists()
