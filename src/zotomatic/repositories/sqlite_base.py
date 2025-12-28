from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Mapping

from zotomatic.errors import ZotomaticWatcherStateRepositoryError


class SQLiteConfig(ABC):
    @property
    @abstractmethod
    def sqlite_path(self) -> Path: ...


@dataclass(slots=True)
class SQLiteRepository:
    """SQLite接続とスキーマ初期化を共通化する基底クラス。"""

    config: SQLiteConfig
    _schema_path: Path = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._schema_path = (
            Path(__file__).resolve().parent / "db" / "schema.sql"
        )
        self._ensure_initialized()

    @classmethod
    def from_settings(cls, settings: Mapping[str, object]) -> "SQLiteRepository":
        from .types import WatcherStateRepositoryConfig

        return cls(WatcherStateRepositoryConfig.from_settings(settings))

    def _ensure_initialized(self) -> None:
        sqlite_path = self.config.sqlite_path
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        needs_init = not sqlite_path.exists()
        with sqlite3.connect(sqlite_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys = ON")
            if needs_init or not self._has_table(conn, "files"):
                self._apply_schema(conn)

    def _apply_schema(self, conn: sqlite3.Connection) -> None:
        if not self._schema_path.exists():
            raise ZotomaticWatcherStateRepositoryError(
                f"Schema file not found: {self._schema_path}"
            )
        schema_sql = self._schema_path.read_text(encoding="utf-8")
        conn.executescript(schema_sql)

    def _has_table(self, conn: sqlite3.Connection, name: str) -> bool:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
            (name,),
        ).fetchone()
        return row is not None

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        try:
            conn = sqlite3.connect(self.config.sqlite_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
        except sqlite3.Error as exc:
            raise ZotomaticWatcherStateRepositoryError(
                f"Failed to open SQLite database: {self.config.sqlite_path}"
            ) from exc
        try:
            yield conn
            conn.commit()
        except sqlite3.Error as exc:
            conn.rollback()
            raise ZotomaticWatcherStateRepositoryError(
                f"SQLite operation failed: {self.config.sqlite_path}"
            ) from exc
        finally:
            conn.close()
