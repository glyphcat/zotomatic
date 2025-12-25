"""
PDFストレージの探索情報ログRepository

想定：SQLite
"""

from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Mapping
from typing import Iterator

from zotomatic.errors import WatcherStateRepositoryError

from .types import WatcherFileState, WatcherStateRepositoryConfig


@dataclass(slots=True)
class WatcherStateRepository:
    """SQLiteに保存するPDFストレージの監視記録の読み書きを司る"""

    config: WatcherStateRepositoryConfig
    _schema_path: Path = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._schema_path = self.config.sqlite_path.with_name("schema.sql")
        self._ensure_initialized()

    @classmethod
    def from_settings(cls, settings: Mapping[str, object]) -> "WatcherStateRepository":
        return cls(WatcherStateRepositoryConfig.from_settings(settings))

    def upsert_file_state(self, state: WatcherFileState) -> None:
        """ファイル状態をSQLiteへ書き込む（存在すれば更新）。"""

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

    def get_file_state(self, path: str | Path) -> WatcherFileState | None:
        """指定パスのファイル状態を読み出す。"""

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
            raise WatcherStateRepositoryError(
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
            raise WatcherStateRepositoryError(
                f"Failed to open SQLite database: {self.config.sqlite_path}"
            ) from exc
        try:
            yield conn
            conn.commit()
        except sqlite3.Error as exc:
            conn.rollback()
            raise WatcherStateRepositoryError(
                f"SQLite operation failed: {self.config.sqlite_path}"
            ) from exc
        finally:
            conn.close()


def build_file_state(
    file_path: Path, mtime_ns: int, size: int, sha1: str | None = None
) -> WatcherFileState:
    """現在時刻を last_seen_at に入れてファイル状態を構築する補助関数。"""

    return WatcherFileState(
        file_path=file_path,
        mtime_ns=mtime_ns,
        size=size,
        sha1=sha1,
        last_seen_at=int(time.time()),
    )
