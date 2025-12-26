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
class SqliteWatcherStateRepository:
    """SQLite実装のStateリポジトリの集約。"""

    file_state: FileStateRepository
    directory_state: DirectoryStateRepository
    pending: PendingRepository
    zotero_attachment: ZoteroAttachmentRepository

    @classmethod
    def from_settings(
        cls, settings: Mapping[str, object]
    ) -> "SqliteWatcherStateRepository":
        config = WatcherStateRepositoryConfig.from_settings(settings)
        return cls(
            file_state=FileStateRepository(config),
            directory_state=DirectoryStateRepository(config),
            pending=PendingRepository(config),
            zotero_attachment=ZoteroAttachmentRepository(config),
        )
