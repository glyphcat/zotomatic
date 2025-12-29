from __future__ import annotations

import time
from pathlib import Path

from zotomatic.repositories import PendingEntry
from zotomatic.repositories.watcher_state import PendingStore, WatcherStateRepository


class PendingQueue:
    """pendingテーブルをキューとして扱うサービス。"""

    def __init__(self, repository: PendingStore) -> None:
        self._repository = repository

    @classmethod
    def from_state_repository(
        cls, state_repository: WatcherStateRepository
    ) -> PendingQueue:
        return cls(state_repository.pending)

    def enqueue(self, file_path: str | Path) -> None:
        now = int(time.time())
        entry = PendingEntry(
            file_path=Path(file_path),
            first_seen_at=now,
            last_attempt_at=None,
            next_attempt_at=now,
            attempt_count=0,
            last_error=None,
        )
        self._repository.upsert(entry)

    def get_due(self, now: int | None = None, limit: int = 50) -> list[PendingEntry]:
        if now is None:
            now = int(time.time())
        return self._repository.list_before(now, limit=limit)

    def list_all(self, limit: int = 50) -> list[PendingEntry]:
        return self._repository.list_all(limit=limit)

    def count_all(self) -> int:
        return self._repository.count_all()

    def update_attempt(
        self,
        file_path: str | Path,
        attempt_count: int,
        next_attempt_at: int,
        last_error: str | None = None,
    ) -> None:
        entry = self._repository.get(file_path)
        if entry is None:
            return
        updated = PendingEntry(
            file_path=entry.file_path,
            first_seen_at=entry.first_seen_at,
            last_attempt_at=int(time.time()),
            next_attempt_at=next_attempt_at,
            attempt_count=attempt_count,
            last_error=last_error,
        )
        self._repository.upsert(updated)

    def resolve(self, file_path: str | Path) -> None:
        self._repository.delete(file_path)
