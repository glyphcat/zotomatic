from __future__ import annotations

from pathlib import Path
from typing import Mapping

from ..repository import PendingStore
from ...types import PendingEntry, WatcherStateRepositoryConfig
from zotomatic.repositories.sqlite_base import SQLiteRepository


class SqlitePendingStore(SQLiteRepository, PendingStore):
    """pendingテーブルへのアクセスを担当する。"""

    @classmethod
    def from_settings(cls, settings: Mapping[str, object]) -> SqlitePendingStore:
        return cls(WatcherStateRepositoryConfig.from_settings(settings))

    def upsert(self, entry: PendingEntry) -> None:
        query = """
            INSERT INTO pending (
                file_path,
                first_seen_at,
                last_attempt_at,
                next_attempt_at,
                attempt_count,
                last_error
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                last_attempt_at=excluded.last_attempt_at,
                next_attempt_at=excluded.next_attempt_at,
                attempt_count=excluded.attempt_count,
                last_error=excluded.last_error
        """
        params = (
            str(entry.file_path),
            entry.first_seen_at,
            entry.last_attempt_at,
            entry.next_attempt_at,
            entry.attempt_count,
            entry.last_error,
        )
        with self._connect() as conn:
            conn.execute(query, params)

    def get(self, file_path: str | Path) -> PendingEntry | None:
        resolved = Path(file_path).expanduser()
        query = """
            SELECT
                file_path,
                first_seen_at,
                last_attempt_at,
                next_attempt_at,
                attempt_count,
                last_error
            FROM pending
            WHERE file_path = ?
        """
        with self._connect() as conn:
            row = conn.execute(query, (str(resolved),)).fetchone()
        if row is None:
            return None
        return PendingEntry(
            file_path=Path(row["file_path"]),
            first_seen_at=row["first_seen_at"],
            last_attempt_at=row["last_attempt_at"],
            next_attempt_at=row["next_attempt_at"],
            attempt_count=row["attempt_count"],
            last_error=row["last_error"],
        )

    def list_before(self, timestamp: int, limit: int = 50) -> list[PendingEntry]:
        query = """
            SELECT
                file_path,
                first_seen_at,
                last_attempt_at,
                next_attempt_at,
                attempt_count,
                last_error
            FROM pending
            WHERE next_attempt_at <= ?
            ORDER BY next_attempt_at ASC
            LIMIT ?
        """
        with self._connect() as conn:
            rows = conn.execute(query, (timestamp, limit)).fetchall()
        return [
            PendingEntry(
                file_path=Path(row["file_path"]),
                first_seen_at=row["first_seen_at"],
                last_attempt_at=row["last_attempt_at"],
                next_attempt_at=row["next_attempt_at"],
                attempt_count=row["attempt_count"],
                last_error=row["last_error"],
            )
            for row in rows
        ]

    def list_all(self, limit: int = 50) -> list[PendingEntry]:
        query = """
            SELECT
                file_path,
                first_seen_at,
                last_attempt_at,
                next_attempt_at,
                attempt_count,
                last_error
            FROM pending
            ORDER BY next_attempt_at ASC
            LIMIT ?
        """
        with self._connect() as conn:
            rows = conn.execute(query, (limit,)).fetchall()
        return [
            PendingEntry(
                file_path=Path(row["file_path"]),
                first_seen_at=row["first_seen_at"],
                last_attempt_at=row["last_attempt_at"],
                next_attempt_at=row["next_attempt_at"],
                attempt_count=row["attempt_count"],
                last_error=row["last_error"],
            )
            for row in rows
        ]

    def count_all(self) -> int:
        query = "SELECT COUNT(*) AS count FROM pending"
        with self._connect() as conn:
            row = conn.execute(query).fetchone()
        if row is None:
            return 0
        return int(row["count"] or 0)

    def delete(self, file_path: str | Path) -> None:
        resolved = Path(file_path).expanduser()
        with self._connect() as conn:
            conn.execute("DELETE FROM pending WHERE file_path = ?", (str(resolved),))
