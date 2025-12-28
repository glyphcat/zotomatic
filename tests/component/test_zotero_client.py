from __future__ import annotations

from pathlib import Path

import pytest

from zotomatic.note.types import NoteBuilderContext
from zotomatic.zotero import client as zotero_client
from zotomatic.zotero.types import ZoteroClientConfig, ZoteroPaper


class FakeZoteroAPI:
    def __init__(self, attachments: list[dict]) -> None:
        self._attachments = attachments

    def items(self, **_kwargs):
        return self._attachments

    def everything(self, items):
        return items


def test_create_client_disabled() -> None:
    config = ZoteroClientConfig(library_id="", api_key="")
    client = zotero_client.ZoteroClient(config)
    assert client.is_enabled() is False


def test_find_attachment_by_pdf_path(monkeypatch: pytest.MonkeyPatch) -> None:
    attachments = [
        {
            "data": {
                "linkMode": "linked_file",
                "path": "/tmp/dir/file.pdf",
                "parentItem": "P1",
            },
            "key": "A1",
        },
        {
            "data": {"filename": "other.pdf", "parentItem": "P2"},
            "key": "A2",
        },
    ]
    config = ZoteroClientConfig(library_id="id", api_key="key")
    monkeypatch.setattr(zotero_client.zotero_api, "Zotero", lambda *_a, **_k: object())
    client = zotero_client.ZoteroClient(config)
    client._client = FakeZoteroAPI(attachments)
    attachment, parent = client._find_attachment_by_pdf_path("/tmp/dir/file.pdf")
    assert parent == "P1"
    assert attachment["key"] == "A1"


def test_get_paper_with_attachment_info(monkeypatch: pytest.MonkeyPatch) -> None:
    attachments = [
        {
            "data": {"filename": "file.pdf", "parentItem": "P2"},
            "key": "A2",
        }
    ]
    config = ZoteroClientConfig(library_id="id", api_key="key")
    monkeypatch.setattr(zotero_client.zotero_api, "Zotero", lambda *_a, **_k: object())
    client = zotero_client.ZoteroClient(config)
    client._client = FakeZoteroAPI(attachments)

    sentinel = ZoteroPaper(
        key="K",
        citekey="C",
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
    monkeypatch.setattr(zotero_client.mapper, "build_paper", lambda *_args, **_kwargs: sentinel)

    paper, attachment_key, parent_key = client.get_paper_with_attachment_info(Path("/tmp/file.pdf"))
    assert paper == sentinel
    assert attachment_key == "A2"
    assert parent_key == "P2"


def test_build_context_fallback() -> None:
    config = ZoteroClientConfig(library_id="", api_key="")
    client = zotero_client.ZoteroClient(config)
    context = client.build_context(Path("/tmp/file.pdf"))
    assert isinstance(context, NoteBuilderContext)
    assert context.title == "file"


def test_build_context_enriched(monkeypatch: pytest.MonkeyPatch) -> None:
    paper = ZoteroPaper(
        key="K",
        citekey="C",
        title="Title",
        year="2023",
        authors="Author",
        publicationTitle="Venue",
        DOI=None,
        url="https://example.com",
        abstractNote="Abstract",
        collections=["C1"],
        zoteroSelectURI="uri",
        filePath="/tmp/file.pdf",
        annotations=[],
    )
    config = ZoteroClientConfig(library_id="id", api_key="key")
    monkeypatch.setattr(zotero_client.zotero_api, "Zotero", lambda *_a, **_k: object())
    client = zotero_client.ZoteroClient(config)
    monkeypatch.setattr(client, "get_paper_by_pdf", lambda _p: paper)
    monkeypatch.setattr(zotero_client, "enrich_paper_metadata", lambda p: p)
    monkeypatch.setattr(zotero_client, "derive_source_url", lambda p: p.url or "")
    monkeypatch.setattr(zotero_client, "render_annotations", lambda annotations: "")

    context = client.build_context(Path("/tmp/file.pdf"))
    assert context is not None
    assert context.citekey == "C"
    assert context.url == "https://example.com"
