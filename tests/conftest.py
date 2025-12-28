from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def default_settings(tmp_path: Path) -> dict[str, str]:
    template = tmp_path / "note.md"
    template.write_text("---\n---\n{title}\n", encoding="utf-8")
    return {
        "note_dir": str(tmp_path / "notes"),
        "pdf_dir": str(tmp_path / "pdfs"),
        "note_title_pattern": "{{ title }}",
        "template_path": str(template),
    }


@pytest.fixture
def sqlite_schema_path(monkeypatch: pytest.MonkeyPatch) -> Path:
    from zotomatic.repositories import sqlite_base

    schema_path = ROOT / "src" / "zotomatic" / "db" / "schema.sql"

    def _patched_post_init(self) -> None:
        self._schema_path = schema_path
        self._ensure_initialized()

    monkeypatch.setattr(
        sqlite_base.SQLiteRepository, "__post_init__", _patched_post_init, raising=True
    )
    return schema_path
