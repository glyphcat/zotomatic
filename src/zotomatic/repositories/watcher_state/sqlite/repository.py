from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ...types import WatcherStateRepositoryConfig
from ..repository import WatcherStateRepository
from .directory_state import DirectoryStateRepository
from .file_state import FileStateRepository
from .pending import PendingRepository
from .zotero_attachment import ZoteroAttachmentRepository


@dataclass(slots=True)
class SqliteWatcherStateRepository(WatcherStateRepository):
    """SQLite実装のStateリポジトリの集約。"""

    _file_state: FileStateRepository
    _directory_state: DirectoryStateRepository
    _pending: PendingRepository
    _zotero_attachment: ZoteroAttachmentRepository

    @classmethod
    def from_settings(
        cls, settings: Mapping[str, object]
    ) -> SqliteWatcherStateRepository:
        config = WatcherStateRepositoryConfig.from_settings(settings)
        return cls(
            _file_state=FileStateRepository(config),
            _directory_state=DirectoryStateRepository(config),
            _pending=PendingRepository(config),
            _zotero_attachment=ZoteroAttachmentRepository(config),
        )

    @property
    def file_state(self) -> FileStateRepository:
        return self._file_state

    @property
    def directory_state(self) -> DirectoryStateRepository:
        return self._directory_state

    @property
    def pending(self) -> PendingRepository:
        return self._pending

    @property
    def zotero_attachment(self) -> ZoteroAttachmentRepository:
        return self._zotero_attachment
