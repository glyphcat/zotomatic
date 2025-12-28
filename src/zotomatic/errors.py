# src/zotomatic/errors.py
from __future__ import annotations


class ZotomaticError(Exception):
    """Base exception for all zotomatic errors."""

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.hint = hint


class ZotomaticConfigError(ZotomaticError):
    """Raised when config is missing or invalid."""


class ZotomaticMissingSettingError(ZotomaticConfigError):
    """Raised when a required configuration value is absent."""

    def __init__(
        self,
        setting_name: str,
        message: str | None = None,
        hint: str | None = None,
    ) -> None:
        detail = message or f"Missing required setting: {setting_name}"
        hint = hint or (
            f"Set `{setting_name}` in ~/.zotomatic/config.toml or export "
            f"ZOTOMATIC_{setting_name.upper()}."
        )
        super().__init__(detail, hint=hint)
        self.setting_name = setting_name


class ZotomaticZoteroError(ZotomaticError):
    """Raised when Zotero cannot be accessed."""


class ZotomaticNoteGenerationError(ZotomaticError):
    """Raised when note creation fails."""


class ZotomaticNoteBuilderError(ZotomaticNoteGenerationError):
    """Raised when note building fails."""


class ZotomaticNoteWorkflowError(ZotomaticNoteGenerationError):
    """Raised when note workflow fails."""


class ZotomaticWatcherError(ZotomaticError):
    """Raised when the filesystem watcher cannot start or continue running."""


class ZotomaticRepositoryError(ZotomaticError):
    """Base error for repository related failures."""


class ZotomaticNoteRepositoryError(ZotomaticRepositoryError):
    """Raised when note repository cannot complete an operation."""


class ZotomaticPDFRepositoryError(ZotomaticRepositoryError):
    """Raised when PDF repository cannot complete an operation."""


class ZotomaticWatcherStateRepositoryError(ZotomaticRepositoryError):
    """Raised when watcher state repository cannot complete an operation."""


class ZotomaticLLMError(ZotomaticError):
    """Base error for LLM related failures."""


class ZotomaticLLMConfigError(ZotomaticLLMError):
    """Raised when LLM configuration is missing or invalid."""


class ZotomaticLLMClientError(ZotomaticLLMError):
    """Base error for LLM client failures."""


class ZotomaticLLMAPIError(ZotomaticLLMClientError):
    """Raised when the HTTP API call fails."""


class ZotomaticLLMResponseFormatError(ZotomaticLLMClientError):
    """Raised when the response payload is not in the expected shape."""


class ZotomaticLLMUnsupportedProviderError(ZotomaticLLMClientError):
    """Raised when the requested provider is not supported."""


class ZotomaticLLMUsageError(ZotomaticLLMError):
    """Raised when LLM usage tracking is invalid."""


class ZotomaticCLIError(ZotomaticError):
    """Raised when CLI usage is invalid."""
