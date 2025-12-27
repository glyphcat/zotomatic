from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ...types import WatcherStateRepositoryConfig
from ..repository import MetaStore, WatcherStateRepository
from .directory_state import SqliteDirectoryStateStore
from .file_state import SqliteFileStateStore
from .meta import SqliteMetaStore
from .pending import SqlitePendingStore
from .zotero_attachment import SqliteZoteroAttachmentStore


@dataclass(slots=True)
class SqliteWatcherStateRepository(WatcherStateRepository):
    """SQLite実装のStateリポジトリの集約。"""

    _file_state: SqliteFileStateStore
    _directory_state: SqliteDirectoryStateStore
    _pending: SqlitePendingStore
    _meta: SqliteMetaStore
    _zotero_attachment: SqliteZoteroAttachmentStore

    @classmethod
    def from_settings(
        cls, settings: Mapping[str, object]
    ) -> SqliteWatcherStateRepository:
        config = WatcherStateRepositoryConfig.from_settings(settings)
        return cls(
            _file_state=SqliteFileStateStore(config),
            _directory_state=SqliteDirectoryStateStore(config),
            _pending=SqlitePendingStore(config),
            _meta=SqliteMetaStore(config),
            _zotero_attachment=SqliteZoteroAttachmentStore(config),
        )

    @property
    def file_state(self) -> SqliteFileStateStore:
        return self._file_state

    @property
    def directory_state(self) -> SqliteDirectoryStateStore:
        return self._directory_state

    @property
    def pending(self) -> SqlitePendingStore:
        return self._pending

    @property
    def meta(self) -> SqliteMetaStore:
        return self._meta

    @property
    def zotero_attachment(self) -> SqliteZoteroAttachmentStore:
        return self._zotero_attachment
