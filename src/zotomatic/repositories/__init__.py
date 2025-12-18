"""Public interface for zotomatic repositories."""

from .note_repository import NoteRepository
from .pdf_repository import PDFRepository
from .types import NoteRepositoryConfig, PDFRepositoryConfig

__all__ = [
    "NoteRepository",
    "PDFRepository",
    "NoteRepositoryConfig",
    "PDFRepositoryConfig",
]
