from __future__ import annotations

from pathlib import Path
from typing import Mapping

from ..repository import DirectoryStateStore
from ...types import DirectoryState, WatcherStateRepositoryConfig
from .base import SQLiteRepository


class SqliteDirectoryStateStore(SQLiteRepository, DirectoryStateStore):
    """directory_stateテーブルへのアクセスを担当する。"""

    @classmethod
    def from_settings(cls, settings: Mapping[str, object]) -> SqliteDirectoryStateStore:
        return cls(WatcherStateRepositoryConfig.from_settings(settings))

    def upsert(self, state: DirectoryState) -> None:
        query = """
            INSERT INTO directory_state (dir_path, aggregated_mtime_ns, last_seen_at)
            VALUES (?, ?, ?)
            ON CONFLICT(dir_path) DO UPDATE SET
                aggregated_mtime_ns=excluded.aggregated_mtime_ns,
                last_seen_at=excluded.last_seen_at
        """
        params = (str(state.dir_path), state.aggregated_mtime_ns, state.last_seen_at)
        with self._connect() as conn:
            conn.execute(query, params)

    def get(self, dir_path: str | Path) -> DirectoryState | None:
        resolved = Path(dir_path).expanduser()
        query = """
            SELECT dir_path, aggregated_mtime_ns, last_seen_at
            FROM directory_state
            WHERE dir_path = ?
        """
        with self._connect() as conn:
            row = conn.execute(query, (str(resolved),)).fetchone()
        if row is None:
            return None
        return DirectoryState(
            dir_path=Path(row["dir_path"]),
            aggregated_mtime_ns=row["aggregated_mtime_ns"],
            last_seen_at=row["last_seen_at"],
        )
