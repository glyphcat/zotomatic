"""Minimal slugify helper."""

from __future__ import annotations

import re
import unicodedata

_SLUG_REGEX = re.compile(r"[^a-z0-9]+")


def slugify(value: str, max_length: int | None = None) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower()
    slug = _SLUG_REGEX.sub("-", ascii_text).strip("-")
    if max_length is not None and max_length > 0:
        slug = slug[:max_length]
    return slug or "note"
