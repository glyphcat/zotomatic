from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from zotomatic.repositories.types import PendingEntry
from zotomatic.services.pending_queue import PendingQueue


@dataclass
class MemoryPendingStore:
    data: dict[str, PendingEntry]

    def upsert(self, entry: PendingEntry) -> None:
        self.data[str(entry.file_path)] = entry

    def get(self, file_path: str | Path):
        return self.data.get(str(Path(file_path)))

    def list_before(self, timestamp: int, limit: int = 50):
        entries = [e for e in self.data.values() if e.next_attempt_at <= timestamp]
        return sorted(entries, key=lambda e: e.next_attempt_at)[:limit]

    def delete(self, file_path: str | Path) -> None:
        self.data.pop(str(Path(file_path)), None)


def test_pending_queue_enqueue_and_resolve(tmp_path: Path) -> None:
    store = MemoryPendingStore(data={})
    queue = PendingQueue(store)
    pdf_path = tmp_path / "paper.pdf"
    queue.enqueue(pdf_path)
    assert store.get(pdf_path) is not None

    due = queue.get_due(limit=10)
    assert len(due) == 1

    queue.resolve(pdf_path)
    assert store.get(pdf_path) is None


def test_pending_queue_update_attempt(tmp_path: Path) -> None:
    store = MemoryPendingStore(data={})
    queue = PendingQueue(store)
    pdf_path = tmp_path / "paper.pdf"
    queue.enqueue(pdf_path)
    entry = store.get(pdf_path)
    queue.update_attempt(pdf_path, attempt_count=2, next_attempt_at=123, last_error="err")
    updated = store.get(pdf_path)
    assert updated is not None
    assert updated.attempt_count == 2
    assert updated.last_error == "err"
    assert updated.last_attempt_at is not None
    assert entry is not None
