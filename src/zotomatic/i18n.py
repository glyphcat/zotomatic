"""Basic utilities for language display names."""

from __future__ import annotations

from zotomatic.errors import ZotomaticError

_LANGUAGE_DISPLAY_MAP = {
    "en": "English",
    "ja": "Japanese",
    "zh": "Chinese",
}
_DEFAULT_LANGUAGE_CODE = "en"


def _resolve_language(code: str) -> str:
    normalized = (code or _DEFAULT_LANGUAGE_CODE).strip().lower()
    return _LANGUAGE_DISPLAY_MAP.get(normalized, normalized)


def get_language_display(code: str) -> str:
    """
    Return a human-readable language name for a given language code.

    Default value is "English".
    """

    display = _resolve_language(code)
    return display
