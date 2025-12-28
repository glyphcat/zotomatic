from __future__ import annotations

from pathlib import Path

import pytest

from zotomatic.utils import pdf


class FakePage:
    def __init__(self, text: str) -> None:
        self._text = text

    def get_text(self, kind: str):
        if kind == "text":
            return self._text
        return {"blocks": []}


class FakeDoc:
    def __init__(self, pages: list[FakePage]) -> None:
        self._pages = pages
        self.page_count = len(pages)

    def load_page(self, i: int) -> FakePage:
        return self._pages[i]

    def close(self) -> None:
        return None


def test_extract_plain_text(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_open(_path):
        return FakeDoc([FakePage("a"), FakePage("b")])

    monkeypatch.setattr(pdf.fitz, "open", fake_open)
    assert pdf.extract_plain_text(tmp_path / "sample.pdf") == "a\nb"


def test_extract_abstract_candidate_with_heading(monkeypatch: pytest.MonkeyPatch) -> None:
    text = """Abstract
This is an abstract line.
Intro
More text
"""
    monkeypatch.setattr(pdf, "extract_plain_text", lambda _p: text)
    monkeypatch.setattr(pdf, "_iter_headings", lambda lines, path: [0, 2])
    result = pdf.extract_abstract_candidate("dummy.pdf")
    assert result.startswith("This is an abstract")


def test_extract_abstract_candidate_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    text = """Line one
Line two
Line three
Line four
"""
    monkeypatch.setattr(pdf, "extract_plain_text", lambda _p: text)
    monkeypatch.setattr(pdf, "_iter_headings", lambda lines, path: [])
    result = pdf.extract_abstract_candidate("dummy.pdf")
    assert result == "Line one\nLine two\nLine three"


def test_extract_section_snippets(monkeypatch: pytest.MonkeyPatch) -> None:
    text = """Intro
first
second
Methods
third
fourth
"""
    monkeypatch.setattr(pdf, "extract_plain_text", lambda _p: text)
    monkeypatch.setattr(pdf, "_iter_headings", lambda lines, path: [0, 3])
    snippets = pdf.extract_section_snippets("dummy.pdf", max_sections=2)
    assert snippets[0].title == "Intro"
    assert "first" in snippets[0].preview


def test_iter_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pdf, "extract_plain_text", lambda _p: "abcdefghij")
    chunks = list(pdf.iter_chunks("dummy.pdf", max_chars=4))
    assert chunks == ["abcd", "efgh", "ij"]


def test_extract_year_candidate_from_text() -> None:
    assert pdf.extract_year_candidate_from_text("Published 2021") == "2021"


def test_extract_authors_candidate_from_text() -> None:
    text = """Title
Alice, Bob
Abstract
"""
    assert pdf.extract_authors_candidate_from_text(text) == "Alice, Bob"
