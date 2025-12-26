from __future__ import annotations

from pathlib import Path
from typing import Mapping

from .base import SQLiteRepository
from ...types import WatcherFileState, WatcherStateRepositoryConfig


class FileStateRepository(SQLiteRepository):
    """filesテーブルへのアクセスを担当する。"""

    @classmethod
    def from_settings(cls, settings: Mapping[str, object]) -> "FileStateRepository":
        return cls(WatcherStateRepositoryConfig.from_settings(settings))

    def upsert(self, state: WatcherFileState) -> None:
        query = """
            INSERT INTO files (file_path, mtime_ns, size, sha1, last_seen_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                mtime_ns=excluded.mtime_ns,
                size=excluded.size,
                sha1=excluded.sha1,
                last_seen_at=excluded.last_seen_at
        """
        params = (
            str(state.file_path),
            state.mtime_ns,
            state.size,
            state.sha1,
            state.last_seen_at,
        )
        with self._connect() as conn:
            conn.execute(query, params)

    def get(self, path: str | Path) -> WatcherFileState | None:
        resolved = Path(path).expanduser()
        query = """
            SELECT file_path, mtime_ns, size, sha1, last_seen_at
            FROM files
            WHERE file_path = ?
        """
        with self._connect() as conn:
            row = conn.execute(query, (str(resolved),)).fetchone()
        if row is None:
            return None
        return WatcherFileState(
            file_path=Path(row["file_path"]),
            mtime_ns=row["mtime_ns"],
            size=row["size"],
            sha1=row["sha1"],
            last_seen_at=row["last_seen_at"],
        )
