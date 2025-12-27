# Zoteroライブラリの情報検索とメタデータ読み込みなど、Zoteroとのやり取りを司るClient
import os
import re
from pathlib import Path
from typing import Iterable, Optional, Sequence

from pyzotero import zotero as zotero_api

from zotomatic.note.types import NoteBuilderContext
from zotomatic.zotero.enricher import enrich_paper_metadata
from zotomatic.zotero.types import ZoteroAnnotation, ZoteroClientConfig, ZoteroPaper

# TODO: 変数zot_clientをzotero_clientにリネームする


class ZoteroClient:
    """Minimal Zotero API wrapper used while bringing up the pipeline."""

    def __init__(self, config: ZoteroClientConfig) -> None:
        self._config = config
        self._client = self._create_client(config)

    # TODO: configの生成はインスタンス生成側で行うため下記は削除
    # @classmethod
    # def from_settings(cls, settings: dict[str, object]) -> "ZoteroClient":
    #     return cls(ZoteroClientConfig.from_settings(settings))

    def _create_client(self, config: ZoteroClientConfig):
        if not config.enabled:
            return None
        try:
            return zotero_api.Zotero(
                config.library_id, config.library_type, config.api_key
            )
        except Exception:  # pragma: no cover - pyzotero runtime error
            return None

    def is_enabled(self) -> bool:
        return self._client is not None

    def get_paper_by_pdf(self, pdf_path: Path) -> Optional[ZoteroPaper]:
        if self._client is None:
            return None
        return _find_by_pdf_path(str(pdf_path), self._client)

    def get_paper_with_attachment_info(
        self, pdf_path: Path
    ) -> tuple[ZoteroPaper | None, str | None, str | None]:
        if self._client is None:
            return None, None, None
        attachment, parent_key = _find_attachment_by_pdf_path(
            str(pdf_path), self._client
        )
        if not parent_key:
            return None, None, None
        paper = _build(self._client, parent_key, str(pdf_path))
        attachment_key = attachment.get("key") if attachment else None
        return paper, attachment_key, parent_key

    def build_context(self, pdf_path: Path) -> NoteBuilderContext | None:
        """Build context for NoteBuilder."""
        paper = self.get_paper_by_pdf(pdf_path)
        if not paper:
            return NoteBuilderContext(
                title=pdf_path.stem,
                pdf_path=str(pdf_path),
                tags=(),
            )

        # TODO: 処理が遅くなる可能性あるためここの補完処理はomitすることを検討
        enriched = enrich_paper_metadata(paper)
        tags = tuple(paper.collections)
        citekey = enriched.citekey or paper.citekey or paper.key or ""
        return NoteBuilderContext(
            title=enriched.title or pdf_path.stem,
            citekey=citekey,
            year=enriched.year or "",
            authors=enriched.authors,
            venue=enriched.publicationTitle or "",
            doi=enriched.DOI or "",
            url=enriched.url or "",
            source_url=_derive_source_url(enriched),
            zotero_select_uri=enriched.zoteroSelectURI,
            pdf_path=enriched.filePath or str(pdf_path),
            abstract=enriched.abstractNote or "",
            highlights=_render_annotations(enriched.annotations),
            tags=tags,
        )


# TODO: PDF読み込みで読み込んだファイル名からZotero内を検索して突合する処理など
# TODO: 下記のメソッドをZoteroClientあるいはUtils/に移譲


# --- PJ7スクリプトから移植した処理。使用できそうなら再利用する ---
def _authors_str(creators):
    names = []
    for c in creators or []:
        if "lastName" in c and "firstName" in c:
            names.append(f"{c['firstName']} {c['lastName']}")
        elif "name" in c:
            names.append(c["name"])
    return ", ".join(names)


def _extract_year(date_str: str) -> Optional[str]:
    if not date_str:
        return None
    m = re.search(r"\d{4}", date_str)
    return m.group(0) if m else None


def _find_by_pdf_path(pdf_path: str, zot_client) -> Optional[ZoteroPaper]:
    attachment, parent = _find_attachment_by_pdf_path(pdf_path, zot_client)
    if not parent:
        return None
    return _build(zot_client, parent, pdf_path)


def _find_attachment_by_pdf_path(pdf_path: str, zot_client) -> tuple[dict | None, str | None]:
    base = os.path.basename(pdf_path)
    pdf_path_n = os.path.normpath(pdf_path)

    # 添付を走査
    try:
        attachments = zot_client.everything(zot_client.items(itemType="attachment"))
    except Exception:  # pragma: no cover - pyzotero runtime error
        return None, None

    # 1) パス末尾一致
    for att in attachments:
        d = att.get("data", {})
        if d.get("linkMode") == "linked_file":
            ap = os.path.normpath(d.get("path") or "")
            if pdf_path_n.endswith(ap) or os.path.basename(ap) == base:
                parent = d.get("parentItem")
                if parent:
                    return att, parent

    # 2) ファイル名一致
    for att in attachments:
        d = att.get("data", {})
        if os.path.basename(d.get("path") or d.get("filename") or "") == base:
            parent = d.get("parentItem")
            if parent:
                return att, parent

    return None, None


def _build(zot_client, item_key: str, pdf_path: str) -> ZoteroPaper:
    item = zot_client.item(item_key)
    data, meta = item.get("data", {}), item.get("meta", {})
    creators = data.get("creators", [])
    citekey = meta.get("citationKey")
    year = _extract_year(data.get("date"))
    annotations: list[ZoteroAnnotation] = []
    try:
        children = zot_client.children(item_key)
    except Exception:  # pragma: no cover
        children = []
    for ch in children:
        if ch.get("data", {}).get("itemType") == "annotation":
            d = ch["data"]
            annotations.append(
                ZoteroAnnotation(
                    pageLabel=d.get("pageLabel"),
                    text=d.get("text") or "",
                    comment=d.get("comment"),
                )
            )
    return ZoteroPaper(
        key=item["key"],
        citekey=citekey,
        title=data.get("title") or "",
        year=year,
        authors=_authors_str(creators),
        publicationTitle=data.get("publicationTitle"),
        DOI=data.get("DOI"),
        url=data.get("url"),
        abstractNote=data.get("abstractNote"),
        collections=data.get("collections") or [],
        zoteroSelectURI=f"zotero://select/library/items/{item['key']}",
        filePath=pdf_path,
        annotations=annotations,
    )


def _render_annotations(annotations: Iterable[ZoteroAnnotation]) -> str:
    highlights = []
    for ann in annotations:
        text = ann.text.strip()
        if not text:
            continue
        if ann.pageLabel:
            highlights.append(f"- p.{ann.pageLabel}: {text}")
        else:
            highlights.append(f"- {text}")
    return "\n".join(highlights)


def _derive_source_url(paper: ZoteroPaper) -> str:
    if paper.url:
        return paper.url
    if paper.DOI:
        return f"https://doi.org/{paper.DOI}"
    return ""
