"""Public interface for zotomatic repositories."""

from .note_repository import NoteRepository
from .pdf_repository import PDFRepository
from .types import (
    NoteRepositoryConfig,
    PDFRepositoryConfig,
    DirectoryState,
    WatcherFileState,
    WatcherStateRepositoryConfig,
)
from .watcher_state_repository import WatcherStateRepository

__all__ = [
    "NoteRepository",
    "PDFRepository",
    "NoteRepositoryConfig",
    "PDFRepositoryConfig",
    "DirectoryState",
    "WatcherStateRepository",
    "WatcherStateRepositoryConfig",
    "WatcherFileState",
]
