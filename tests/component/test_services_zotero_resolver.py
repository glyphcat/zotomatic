from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from zotomatic.services.zotero_resolver import ZoteroResolver
from zotomatic.zotero.types import ZoteroPaper


@dataclass
class MemoryAttachmentStore:
    last_state = None

    def upsert(self, state):
        self.last_state = state


class FakeClient:
    def __init__(self, paper, attachment_key="A", parent_key="P") -> None:
        self._paper = paper
        self._attachment_key = attachment_key
        self._parent_key = parent_key

    def get_paper_with_attachment_info(self, _pdf_path):
        return self._paper, self._attachment_key, self._parent_key

    def is_enabled(self) -> bool:
        return True


def test_resolver_persists_attachment(tmp_path: Path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_text("x", encoding="utf-8")
    paper = ZoteroPaper(
        key="K",
        citekey=None,
        title="T",
        year=None,
        authors="",
        publicationTitle=None,
        DOI=None,
        url=None,
        abstractNote=None,
        collections=[],
        zoteroSelectURI="uri",
        filePath=str(pdf_path),
        annotations=[],
    )
    store = MemoryAttachmentStore()
    resolver = ZoteroResolver(client=FakeClient(paper), attachment_store=store)
    result = resolver.resolve(pdf_path)
    assert result == paper
    assert store.last_state is not None


def test_resolver_is_enabled() -> None:
    paper = ZoteroPaper(
        key="K",
        citekey=None,
        title="T",
        year=None,
        authors="",
        publicationTitle=None,
        DOI=None,
        url=None,
        abstractNote=None,
        collections=[],
        zoteroSelectURI="uri",
        filePath="/tmp/file.pdf",
        annotations=[],
    )
    resolver = ZoteroResolver(client=FakeClient(paper), attachment_store=MemoryAttachmentStore())
    assert resolver.is_enabled is True
