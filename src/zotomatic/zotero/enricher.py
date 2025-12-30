"""Utilities to enrich Zotero metadata using PDF-derived information."""

from __future__ import annotations

from pathlib import Path

from zotomatic.utils import pdf
from zotomatic.zotero.types import ZoteroPaper


def enrich_paper_metadata(paper: ZoteroPaper) -> ZoteroPaper:
    """Return the ZoteroPaper with missing fields filled when possible."""

    pdf_path = Path(paper.filePath) if paper.filePath else None
    if not pdf_path:
        return paper

    missing_abstract = not paper.abstractNote
    missing_year = not paper.year
    missing_authors = not paper.authors
    missing_title = not paper.title
    if not any([missing_abstract, missing_year, missing_authors, missing_title]):
        return paper

    try:
        plain_text = pdf.extract_plain_text(pdf_path)
        abstract_candidate = ""
        if missing_abstract:
            abstract_candidate = pdf.extract_abstract_candidate(
                pdf_path, text=plain_text
            )
    except Exception:  # pragma: no cover - corrupted or unsupported PDF
        return paper

    updates: dict[str, object] = {}

    # NOTE: ZoteroメタデータよりabstractNoteが取得できなかった場合、独自に要約を探索し保管する処理
    if not paper.abstractNote and abstract_candidate:
        updates["abstractNote"] = abstract_candidate

    if not paper.year:
        year = pdf.extract_year_candidate_from_text(plain_text)
        if year:
            updates["year"] = year

    if not paper.authors:
        authors = pdf.extract_authors_candidate_from_text(plain_text)
        if authors:
            updates["authors"] = authors

    if not paper.title and pdf_path.stem:
        updates["title"] = pdf_path.stem

    return paper.update(**updates) if updates else paper
