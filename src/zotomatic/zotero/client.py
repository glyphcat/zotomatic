# Zoteroライブラリの情報検索とメタデータ読み込みなど、Zoteroとのやり取りを司るClient
import os
from pathlib import Path
from typing import Optional

from pyzotero import zotero as zotero_api

from zotomatic.note.types import NoteBuilderContext
from zotomatic.zotero import mapper
from zotomatic.zotero.enricher import enrich_paper_metadata
from zotomatic.zotero.formatters import derive_source_url, render_annotations
from zotomatic.zotero.types import ZoteroClientConfig, ZoteroPaper

# TODO: 変数zot_clientをzotero_clientにリネームする


class ZoteroClient:
    """Minimal Zotero API wrapper used while bringing up the pipeline."""

    def __init__(self, config: ZoteroClientConfig) -> None:
        self._config = config
        self._client: zotero_api.Zotero | None = self._create_client(config)

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
        return self._find_by_pdf_path(str(pdf_path))

    def get_paper_with_attachment_info(
        self, pdf_path: Path
    ) -> tuple[ZoteroPaper | None, str | None, str | None]:
        if self._client is None:
            return None, None, None
        attachment, parent_key = self._find_attachment_by_pdf_path(str(pdf_path))
        if not parent_key:
            return None, None, None
        paper = mapper.build_paper(self._client, parent_key, str(pdf_path))
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
            source_url=derive_source_url(enriched),
            zotero_select_uri=enriched.zoteroSelectURI,
            pdf_path=enriched.filePath or str(pdf_path),
            abstract=enriched.abstractNote or "",
            highlights=render_annotations(enriched.annotations),
            tags=tags,
        )

    def _find_by_pdf_path(self, pdf_path: str) -> Optional[ZoteroPaper]:
        if self._client is None:
            return None
        attachment, parent = self._find_attachment_by_pdf_path(pdf_path)
        if not parent:
            return None
        return mapper.build_paper(self._client, parent, pdf_path)

    def _find_attachment_by_pdf_path(
        self, pdf_path: str
    ) -> tuple[dict | None, str | None]:
        if self._client is None:
            return None, None
        base = os.path.basename(pdf_path)
        pdf_path_n = os.path.normpath(pdf_path)

        # 添付を走査
        try:
            client = self._client
            assert client is not None
            attachments = client.everything(client.items(itemType="attachment"))
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
