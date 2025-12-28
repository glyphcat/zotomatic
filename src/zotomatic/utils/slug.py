"""Minimal slugify helper."""

from __future__ import annotations

import re
import unicodedata

_SLUG_REGEX = re.compile(r"[^a-z0-9]+")
_INVALID_FILENAME_CHARS = re.compile('[<>:"/\\\\|?*\x00-\x1F]')
_WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def slugify(value: str, max_length: int | None = None) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower()
    slug = _SLUG_REGEX.sub("-", ascii_text).strip("-")
    if max_length is not None and max_length > 0:
        slug = slug[:max_length]
    return slug or "note"


def sanitize_filename(value: str, fallback: str = "note") -> str:
    """Sanitize a filename for Windows-compatible filesystems."""
    name = (value or "").strip()
    if not name:
        return fallback
    name = _INVALID_FILENAME_CHARS.sub("-", name)
    name = name.rstrip(" .")
    if not name or name in {".", ".."}:
        return fallback
    stem = name.rsplit(".", 1)[0] if "." in name else name
    if stem.upper() in _WINDOWS_RESERVED:
        name = f"{name}_"
    return name or fallback
