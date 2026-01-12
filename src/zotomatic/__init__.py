"""Zotomatic public API."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("zotomatic")
except PackageNotFoundError:  # pragma: no cover - during source-only use
    __version__ = "unknown"

__all__ = ["__version__"]
