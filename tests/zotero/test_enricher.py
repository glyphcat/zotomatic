from __future__ import annotations

import pytest

from zotomatic.zotero import enricher
from zotomatic.zotero.types import ZoteroPaper


def test_enrich_paper_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    paper = ZoteroPaper(
        key="K",
        citekey=None,
        title="",
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

    monkeypatch.setattr(enricher.pdf, "extract_plain_text", lambda _p: "2021\nAlice, Bob")
    monkeypatch.setattr(
        enricher.pdf, "extract_abstract_candidate", lambda _p, **_kw: "Abstract"
    )
    monkeypatch.setattr(enricher.pdf, "extract_year_candidate_from_text", lambda _t: "2021")
    monkeypatch.setattr(enricher.pdf, "extract_authors_candidate_from_text", lambda _t: "Alice, Bob")

    enriched = enricher.enrich_paper_metadata(paper)
    assert enriched.year == "2021"
    assert enriched.authors == "Alice, Bob"
    assert enriched.abstractNote == "Abstract"
    assert enriched.title == "file"
