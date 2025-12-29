from __future__ import annotations

from pathlib import Path

import pytest

from zotomatic.watcher.types import WatcherConfig
from zotomatic.watcher.watcher import PDFStorageWatcher
from zotomatic.repositories.types import DirectoryState, WatcherFileState


def test_watcher_config_from_settings(tmp_path: Path) -> None:
    settings = {"pdf_dir": str(tmp_path)}
    config = WatcherConfig.from_settings(settings, lambda _p: None)
    assert config.watch_dir == tmp_path


def test_watcher_config_missing_pdf_dir() -> None:
    with pytest.raises(Exception):
        WatcherConfig.from_settings({}, lambda _p: None)


def test_watcher_simulate_pdf_saved(tmp_path: Path) -> None:
    seen: list[Path] = []
    config = WatcherConfig(
        watch_dir=tmp_path,
        on_pdf_created=lambda p: seen.append(p),
        state_repository=None,
    )
    watcher = PDFStorageWatcher(config)
    path = watcher.simulate_pdf_saved("test.pdf")
    assert path.name == "test.pdf"
    assert seen == [path]


def test_handle_candidate_calls_callback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[Path] = []
    config = WatcherConfig(watch_dir=tmp_path, on_pdf_created=seen.append)
    watcher = PDFStorageWatcher(config)

    pdf_path = tmp_path / "file.pdf"
    pdf_path.write_text("data", encoding="utf-8")

    monkeypatch.setattr(watcher, "_wait_for_stable", lambda _p: True)
    watcher._handle_candidate(pdf_path)
    assert seen == [pdf_path.resolve()]


def test_scan_for_new_pdfs_without_state(tmp_path: Path) -> None:
    config = WatcherConfig(watch_dir=tmp_path, on_pdf_created=lambda _p: None)
    watcher = PDFStorageWatcher(config)
    (tmp_path / "a.pdf").write_text("x", encoding="utf-8")
    (tmp_path / "b.txt").write_text("x", encoding="utf-8")
    pdfs = watcher._scan_for_new_pdfs()
    assert len(pdfs) == 1


def test_force_scan_ignores_directory_state(tmp_path: Path) -> None:
    pdf_path = tmp_path / "a.pdf"
    pdf_path.write_text("x", encoding="utf-8")
    current_mtime = tmp_path.stat().st_mtime_ns

    class DummyDirectoryStateRepo:
        def get(self, _path: Path):
            return DirectoryState.from_path(tmp_path, current_mtime)

        def upsert(self, _state: DirectoryState) -> None:
            return None

    class DummyStateRepo:
        directory_state = DummyDirectoryStateRepo()
        file_state = None

    config = WatcherConfig(
        watch_dir=tmp_path,
        on_pdf_created=lambda _p: None,
        state_repository=DummyStateRepo(),
        force_scan=True,
    )
    watcher = PDFStorageWatcher(config)
    pdfs = watcher._scan_for_new_pdfs()
    assert pdfs == [pdf_path]


def test_force_scan_ignores_file_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[Path] = []
    pdf_path = tmp_path / "file.pdf"
    pdf_path.write_text("data", encoding="utf-8")

    state = WatcherFileState.from_path(
        file_path=pdf_path,
        mtime_ns=pdf_path.stat().st_mtime_ns,
        size=pdf_path.stat().st_size,
    )

    class DummyFileStateRepo:
        def __init__(self, stored: WatcherFileState):
            self._stored = stored

        def get(self, _path: Path):
            return self._stored

        def upsert(self, stored: WatcherFileState) -> None:
            self._stored = stored

    class DummyStateRepo:
        def __init__(self, stored: WatcherFileState):
            self.file_state = DummyFileStateRepo(stored)
            self.directory_state = None

    config = WatcherConfig(
        watch_dir=tmp_path,
        on_pdf_created=lambda p: seen.append(p),
        state_repository=DummyStateRepo(state),
        force_scan=True,
    )
    watcher = PDFStorageWatcher(config)
    monkeypatch.setattr(watcher, "_wait_for_stable", lambda _p: True)
    watcher._handle_candidate(pdf_path)
    assert seen == [pdf_path.resolve()]
