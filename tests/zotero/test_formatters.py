from __future__ import annotations

from zotomatic.zotero import formatters
from zotomatic.zotero.types import ZoteroAnnotation, ZoteroPaper


def test_authors_str() -> None:
    creators = [
        {"firstName": "Ada", "lastName": "Lovelace"},
        {"name": "Team"},
    ]
    assert formatters.authors_str(creators) == "Ada Lovelace, Team"


def test_extract_year() -> None:
    assert formatters.extract_year("2020-01-01") == "2020"
    assert formatters.extract_year("") is None


def test_render_annotations() -> None:
    annotations = [
        ZoteroAnnotation(pageLabel="1", text=" highlight ", comment=None),
        ZoteroAnnotation(pageLabel=None, text="note", comment=None),
    ]
    output = formatters.render_annotations(annotations)
    assert "p.1" in output
    assert "note" in output


def test_derive_source_url() -> None:
    paper = ZoteroPaper(
        key="K",
        citekey=None,
        title="T",
        year=None,
        authors="",
        publicationTitle=None,
        DOI="10.1000/xyz",
        url=None,
        abstractNote=None,
        collections=[],
        zoteroSelectURI="uri",
        filePath="/tmp/file.pdf",
        annotations=[],
    )
    assert formatters.derive_source_url(paper) == "https://doi.org/10.1000/xyz"
