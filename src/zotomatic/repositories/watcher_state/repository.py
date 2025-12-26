from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from collections.abc import Mapping

from ..types import DirectoryState, PendingEntry, WatcherFileState, ZoteroAttachmentState


class FileStateStore(ABC):
    @abstractmethod
    def upsert(self, state: WatcherFileState) -> None: ...

    @abstractmethod
    def get(self, path: str | Path) -> WatcherFileState | None: ...

class DirectoryStateStore(ABC):
    @abstractmethod
    def upsert(self, state: DirectoryState) -> None: ...

    @abstractmethod
    def get(self, dir_path: str | Path) -> DirectoryState | None: ...


class PendingStore(ABC):
    @abstractmethod
    def upsert(self, entry: PendingEntry) -> None: ...

    @abstractmethod
    def get(self, file_path: str | Path) -> PendingEntry | None: ...

    @abstractmethod
    def list_before(self, timestamp: int, limit: int = 50) -> list[PendingEntry]: ...

    @abstractmethod
    def delete(self, file_path: str | Path) -> None: ...


class ZoteroAttachmentStore(ABC):
    @abstractmethod
    def upsert(self, state: ZoteroAttachmentState) -> None: ...


class WatcherStateRepository(ABC):
    @property
    @abstractmethod
    def file_state(self) -> FileStateStore: ...

    @property
    @abstractmethod
    def directory_state(self) -> DirectoryStateStore: ...

    @property
    @abstractmethod
    def pending(self) -> PendingStore: ...

    @property
    @abstractmethod
    def zotero_attachment(self) -> ZoteroAttachmentStore: ...


def create_watcher_state_repository(
    settings: Mapping[str, object],
) -> WatcherStateRepository:
    from .sqlite.repository import SqliteWatcherStateRepository

    return SqliteWatcherStateRepository.from_settings(settings)
