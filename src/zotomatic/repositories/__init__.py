"""Public interface for zotomatic repositories."""

from .note_repository import NoteRepository
from .pdf_repository import PDFRepository
from .types import (
    DirectoryState,
    NoteRepositoryConfig,
    PDFRepositoryConfig,
    PendingEntry,
    WatcherFileState,
    WatcherStateRepositoryConfig,
    ZoteroAttachmentState,
)
from .state import WatcherStateRepository, create_watcher_state_repository

__all__ = [
    "NoteRepository",
    "PDFRepository",
    "NoteRepositoryConfig",
    "PDFRepositoryConfig",
    "DirectoryState",
    "PendingEntry",
    "WatcherStateRepository",
    "create_watcher_state_repository",
    "WatcherStateRepositoryConfig",
    "WatcherFileState",
    "ZoteroAttachmentState",
]
