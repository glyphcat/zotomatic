from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from ...types import WatcherStateRepositoryConfig, ZoteroAttachmentState
from ..repository import ZoteroAttachmentStore
from .base import SQLiteRepository


class SqliteZoteroAttachmentStore(SQLiteRepository, ZoteroAttachmentStore):
    """zotero_attachmentテーブルへのアクセスを担当する。"""

    @classmethod
    def from_settings(
        cls, settings: Mapping[str, object]
    ) -> SqliteZoteroAttachmentStore:
        return cls(WatcherStateRepositoryConfig.from_settings(settings))

    def upsert(self, state: ZoteroAttachmentState) -> None:
        query = """
            INSERT INTO zotero_attachment (
                attachment_key,
                parent_item_key,
                file_path,
                mtime_ns,
                size,
                sha1,
                last_seen_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(attachment_key) DO UPDATE SET
                parent_item_key=excluded.parent_item_key,
                file_path=excluded.file_path,
                mtime_ns=excluded.mtime_ns,
                size=excluded.size,
                sha1=excluded.sha1,
                last_seen_at=excluded.last_seen_at
        """
        params = (
            state.attachment_key,
            state.parent_item_key,
            str(state.file_path) if state.file_path else None,
            state.mtime_ns,
            state.size,
            state.sha1,
            state.last_seen_at,
        )
        with self._connect() as conn:
            conn.execute(query, params)

    def get(self, attachment_key: str) -> ZoteroAttachmentState | None:
        query = """
            SELECT
                attachment_key,
                parent_item_key,
                file_path,
                mtime_ns,
                size,
                sha1,
                last_seen_at
            FROM zotero_attachment
            WHERE attachment_key = ?
        """
        with self._connect() as conn:
            row = conn.execute(query, (attachment_key,)).fetchone()
        if row is None:
            return None
        return ZoteroAttachmentState(
            attachment_key=row["attachment_key"],
            parent_item_key=row["parent_item_key"],
            file_path=Path(row["file_path"]) if row["file_path"] else None,
            mtime_ns=row["mtime_ns"],
            size=row["size"],
            sha1=row["sha1"],
            last_seen_at=row["last_seen_at"],
        )
