from __future__ import annotations

from collections.abc import Mapping

from ..repository import MetaStore
from .base import SQLiteRepository
from ...types import WatcherStateRepositoryConfig


class SqliteMetaStore(SQLiteRepository, MetaStore):
    """metaテーブルへのアクセスを担当する。"""

    @classmethod
    def from_settings(cls, settings: Mapping[str, object]) -> "SqliteMetaStore":
        return cls(WatcherStateRepositoryConfig.from_settings(settings))

    def get(self, key: str) -> str | None:
        query = "SELECT value FROM meta WHERE key = ?"
        with self._connect() as conn:
            row = conn.execute(query, (key,)).fetchone()
        if row is None:
            return None
        return str(row["value"])

    def set(self, key: str, value: str) -> None:
        query = """
            INSERT INTO meta (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """
        with self._connect() as conn:
            conn.execute(query, (key, value))
