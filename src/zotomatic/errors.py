# src/zotomatic/errors.py
from __future__ import annotations
class ZotomaticError(Exception):
    """Base exception for all zotomatic errors."""


class ConfigError(ZotomaticError):
    """Raised when config is missing or invalid."""


class MissingSettingError(ConfigError):
    """Raised when a required configuration value is absent."""

    def __init__(self, setting_name: str, message: str | None = None) -> None:
        detail = message or f"Missing required setting: {setting_name}"
        super().__init__(detail)
        self.setting_name = setting_name


class ZoteroError(ZotomaticError):
    """Raised when Zotero cannot be accessed."""


class NoteGenerationError(ZotomaticError):
    """Raised when note creation fails."""


class WatcherError(ZotomaticError):
    """Raised when the filesystem watcher cannot start or continue running."""


class RepositoryError(ZotomaticError):
    """Base error for repository related failures."""


class NoteRepositoryError(RepositoryError):
    """Raised when note repository cannot complete an operation."""


class PDFRepositoryError(RepositoryError):
    """Raised when PDF repository cannot complete an operation."""


class WatcherStateRepositoryError(RepositoryError):
    """Raised when watcher state repository cannot complete an operation."""


class LLMClientError(RuntimeError):
    """Base error for LLM client failures."""


class LLMAPIError(LLMClientError):
    """Raised when the HTTP API call fails."""


class LLMResponseFormatError(LLMClientError):
    """Raised when the response payload is not in the expected shape."""


class UnsupportedProviderError(LLMClientError):
    """Raised when the requested provider is not supported."""
