from __future__ import annotations

from pathlib import Path

import pytest

from zotomatic.repositories import NoteRepository, PDFRepository
from zotomatic.repositories.types import NoteRepositoryConfig, PDFRepositoryConfig
from zotomatic.errors import ZotomaticPDFRepositoryError


def test_note_repository_write_and_index(tmp_path: Path) -> None:
    repo = NoteRepository(NoteRepositoryConfig(root_dir=tmp_path / "notes"))
    path = repo.write("note.md", "---\ncitekey: A\n---\n")
    assert path.exists()

    index = repo.build_citekey_index()
    assert index["A"] == path
    assert repo.find_by_citekey("A") == path


def test_pdf_repository_read_and_list(tmp_path: Path) -> None:
    library = tmp_path / "library"
    library.mkdir()
    pdf_path = library / "paper.pdf"
    pdf_path.write_bytes(b"data")

    repo = PDFRepository(PDFRepositoryConfig(library_dir=library, recursive=False))
    assert repo.read_bytes("paper.pdf") == b"data"
    assert repo.resolve("paper.pdf") == pdf_path
    assert list(repo.list_pdfs()) == [pdf_path]


def test_pdf_repository_missing(tmp_path: Path) -> None:
    repo = PDFRepository(PDFRepositoryConfig(library_dir=tmp_path, recursive=False))
    with pytest.raises(ZotomaticPDFRepositoryError):
        repo.read_bytes("missing.pdf")
