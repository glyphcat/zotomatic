"""Public interface for zotomatic repositories."""

from .note_repository import NoteRepository
from .pdf_repository import PDFRepository
from .types import (
    DirectoryState,
    LLMUsageEntry,
    LLMUsageRepositoryConfig,
    NoteRepositoryConfig,
    PDFRepositoryConfig,
    PendingEntry,
    WatcherFileState,
    WatcherStateRepositoryConfig,
    ZoteroAttachmentState,
)
from .llm_usage import LLMUsageRepository, create_llm_usage_repository
from .watcher_state import WatcherStateRepository, create_watcher_state_repository

__all__ = [
    "NoteRepository",
    "PDFRepository",
    "NoteRepositoryConfig",
    "PDFRepositoryConfig",
    "DirectoryState",
    "LLMUsageEntry",
    "LLMUsageRepository",
    "LLMUsageRepositoryConfig",
    "PendingEntry",
    "WatcherStateRepository",
    "create_watcher_state_repository",
    "WatcherStateRepositoryConfig",
    "WatcherFileState",
    "ZoteroAttachmentState",
    "create_llm_usage_repository",
]
