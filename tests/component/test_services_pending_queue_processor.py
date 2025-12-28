from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

import pytest

from zotomatic.repositories.types import PendingEntry
from zotomatic.services.pending_queue_processor import PendingQueueProcessor
from zotomatic.services.types import PendingQueueProcessorConfig


@dataclass
class FakeQueue:
    entries: list[PendingEntry]
    resolved: list[Path]
    updates: list[dict]

    def get_due(self, limit: int = 50):
        return self.entries[:limit]

    def update_attempt(self, file_path, attempt_count, next_attempt_at, last_error=None):
        self.updates.append(
            {
                "file_path": Path(file_path),
                "attempt_count": attempt_count,
                "next_attempt_at": next_attempt_at,
                "last_error": last_error,
            }
        )

    def resolve(self, file_path):
        self.resolved.append(Path(file_path))


@dataclass
class FakeResolver:
    is_enabled: bool
    result: object | None

    def resolve(self, _pdf_path):
        return self.result


def _entry(path: Path, attempt_count: int = 0) -> PendingEntry:
    return PendingEntry(
        file_path=path,
        first_seen_at=0,
        last_attempt_at=None,
        next_attempt_at=0,
        attempt_count=attempt_count,
        last_error=None,
    )


def test_processor_drops_when_resolver_disabled(tmp_path: Path) -> None:
    pdf_path = tmp_path / "a.pdf"
    pdf_path.write_text("x", encoding="utf-8")
    queue = FakeQueue(entries=[_entry(pdf_path)], resolved=[], updates=[])
    resolver = FakeResolver(is_enabled=False, result=None)
    processor = PendingQueueProcessor(queue, resolver, lambda _p: None)
    processed = processor.run_once()
    assert processed == 0
    assert queue.resolved == [pdf_path]


def test_processor_backoff_when_unresolved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pdf_path = tmp_path / "a.pdf"
    pdf_path.write_text("x", encoding="utf-8")
    queue = FakeQueue(entries=[_entry(pdf_path, attempt_count=1)], resolved=[], updates=[])
    resolver = FakeResolver(is_enabled=True, result=None)
    processor = PendingQueueProcessor(queue, resolver, lambda _p: None)

    monkeypatch.setattr("zotomatic.services.pending_queue_processor.time.time", lambda: 100)
    monkeypatch.setattr(
        PendingQueueProcessor, "_is_pdf_readable", lambda self, path: True
    )

    processed = processor.run_once()
    assert processed == 0
    assert queue.updates
    assert queue.updates[0]["attempt_count"] == 2


def test_processor_resolves_and_calls_callback(tmp_path: Path) -> None:
    pdf_path = tmp_path / "a.pdf"
    pdf_path.write_text("x", encoding="utf-8")
    queue = FakeQueue(entries=[_entry(pdf_path)], resolved=[], updates=[])
    resolver = FakeResolver(is_enabled=True, result={"paper": True})
    seen: list[Path] = []

    processor = PendingQueueProcessor(queue, resolver, lambda p: seen.append(p))
    processor._is_pdf_readable = lambda _path: True  # type: ignore[assignment]
    processed = processor.run_once()
    assert processed == 1
    assert seen == [pdf_path]
    assert queue.resolved == [pdf_path]


def test_processor_drops_unreadable_pdf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pdf_path = tmp_path / "a.pdf"
    pdf_path.write_text("x", encoding="utf-8")

    def fake_open(_path):
        raise RuntimeError("bad pdf")

    monkeypatch.setattr("zotomatic.services.pending_queue_processor.fitz.open", fake_open)

    queue = FakeQueue(entries=[_entry(pdf_path)], resolved=[], updates=[])
    resolver = FakeResolver(is_enabled=True, result=None)
    processor = PendingQueueProcessor(queue, resolver, lambda _p: None)
    processed = processor.run_once()
    assert processed == 0
    assert queue.resolved == [pdf_path]


def test_processor_stops_on_event(tmp_path: Path) -> None:
    pdf_path = tmp_path / "a.pdf"
    pdf_path.write_text("x", encoding="utf-8")
    queue = FakeQueue(entries=[_entry(pdf_path)], resolved=[], updates=[])
    resolver = FakeResolver(is_enabled=True, result={"paper": True})
    stop_event = threading.Event()
    stop_event.set()
    processor = PendingQueueProcessor(queue, resolver, lambda _p: None, stop_event=stop_event)
    processed = processor.run_once()
    assert processed == 0
