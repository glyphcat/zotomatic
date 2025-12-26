from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable
from collections.abc import Mapping

from ..types import DirectoryState, PendingEntry, WatcherFileState, ZoteroAttachmentState


@runtime_checkable
class FileStateStore(Protocol):
    def upsert(self, state: WatcherFileState) -> None: ...

    def get(self, path: str | Path) -> WatcherFileState | None: ...


@runtime_checkable
class DirectoryStateStore(Protocol):
    def upsert(self, state: DirectoryState) -> None: ...

    def get(self, dir_path: str | Path) -> DirectoryState | None: ...


@runtime_checkable
class PendingStore(Protocol):
    def upsert(self, entry: PendingEntry) -> None: ...

    def get(self, file_path: str | Path) -> PendingEntry | None: ...

    def list_before(self, timestamp: int, limit: int = 50) -> list[PendingEntry]: ...

    def delete(self, file_path: str | Path) -> None: ...


@runtime_checkable
class ZoteroAttachmentStore(Protocol):
    def upsert(self, state: ZoteroAttachmentState) -> None: ...


class WatcherStateRepository(Protocol):
    file_state: FileStateStore
    directory_state: DirectoryStateStore
    pending: PendingStore
    zotero_attachment: ZoteroAttachmentStore


def create_watcher_state_repository(
    settings: Mapping[str, object],
) -> WatcherStateRepository:
    from .sqlite.repository import SqliteWatcherStateRepository

    return SqliteWatcherStateRepository.from_settings(settings)
