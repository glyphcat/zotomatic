"""Utilities for basic PDF text extraction used by Zotomatic."""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import fitz

LANG_HEADING_KEYWORDS = {
    "en": ("abstract", "summary", "introduction", "conclusion", "related work"),
    "ja": ("概要", "要旨", "序論", "結論", "関連研究"),
    "zh": ("摘要", "概述", "简介", "结论", "相关工作"),
}

# TODO: 下記の見出し候補を言語拡張してから利用する
SECTION_CANDIDATES = [
    r"abstract",
    r"introduction|background|overview|preliminaries",
    r"related work|literature review",
    r"method|methods|materials and methods|approach|model",
    r"experiments?|setup|dataset|data",
    r"results?|findings",
    r"analysis|discussion",
    r"ablation|evaluation",
    r"conclusion|summary|future work|limitations",
]


@dataclass(frozen=True, slots=True)
class SectionSnippet:
    """Represents a lightweight view of a PDF section."""

    title: str
    preview: str


def extract_plain_text(path: str | Path) -> str:
    """Return the full text of the PDF as a single string."""

    pdf_path = Path(path)
    doc = fitz.open(pdf_path)
    try:
        texts: list[str] = []
        for i in range(doc.page_count):
            page = doc.load_page(i)
            page_text = page.get_text("text")  # type: ignore[attr-defined]
            texts.append(page_text)
        return "\n".join(texts)
    finally:
        doc.close()


def extract_abstract_candidate(
    path: str | Path,
    max_chars: int = 1200,
    logger: logging.Logger | None = None,
) -> str:
    """Attempt to pull an abstract section from the PDF."""

    placeholder = "No abstract text was detected in the PDF."
    try:
        text = extract_plain_text(path)
    except Exception as exc:  # pragma: no cover - depends on fitz/io errors
        if logger:
            logger.debug("Failed to extract PDF text for abstract: %s", exc)
        return placeholder

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return placeholder

    try:
        heading_indexes = list(_iter_headings(lines, path))
    except Exception as exc:  # pragma: no cover - fitz dependent
        if logger:
            logger.debug("Failed to detect headings during abstract extraction: %s", exc)
        heading_indexes = []

    for idx in heading_indexes:
        if 0 <= idx < len(lines) and _is_abstract_heading(lines[idx]):
            paragraph = _collect_paragraph(lines, idx + 1, max_chars).strip()
            if paragraph:
                return paragraph

    fallback = "\n".join(lines[:3]).strip()
    if not fallback:
        return placeholder
    return fallback[:max_chars]


def extract_section_snippets(
    path: str | Path,
    max_sections: int = 6,
    preview_chars: int = 280,
) -> list[SectionSnippet]:
    """Heuristically detect section headings and return previews."""

    text = extract_plain_text(path)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    snippets: list[SectionSnippet] = []
    for idx in _iter_headings(lines, path):
        preview = " ".join(lines[idx + 1 : idx + 4])
        snippets.append(
            SectionSnippet(
                title=lines[idx],
                preview=preview[:preview_chars].strip(),
            )
        )
        if len(snippets) >= max_sections:
            break
    return snippets


def iter_chunks(path: str | Path, max_chars: int = 2000) -> Iterable[str]:
    """Yield chunks of text with an upper bound on characters."""

    text = extract_plain_text(path)
    start = 0
    length = len(text)
    while start < length:
        end = min(start + max_chars, length)
        yield text[start:end]
        start = end


def _iter_headings(lines: list[str], path: str | Path) -> Iterable[int]:
    lang_keywords = set(LANG_HEADING_KEYWORDS.get(_detect_language(lines), ()))
    lang_keywords |= set(LANG_HEADING_KEYWORDS["en"])
    doc = fitz.open(path)
    try:
        font_threshold = _estimate_font_threshold(doc)
        text_to_size = _build_font_map(doc)
    finally:
        doc.close()

    for idx, line in enumerate(lines):
        if not line:
            continue
        lower = line.lower()
        if lower in lang_keywords:
            yield idx
            continue
        if text_to_size.get(line, 0) >= font_threshold:
            yield idx
            continue
        if _looks_like_heading(line):
            yield idx


def _estimate_font_threshold(doc: fitz.Document) -> float:
    sizes = []
    for page in doc:
        for block in page.get_text("dict")["blocks"]:  # type: ignore[attr-defined]
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    sizes.append(span.get("size", 0))
    return max(sizes) * 0.9 if sizes else 0


def _build_font_map(doc: fitz.Document) -> dict[str, float]:
    mapping: dict[str, float] = {}
    for page in doc:
        for block in page.get_text("dict")["blocks"]:  # type: ignore[attr-defined]
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if text:
                        mapping[text] = span.get("size", 0)
    return mapping


def _collect_paragraph(lines: list[str], start: int, max_chars: int) -> str:
    collected: list[str] = []
    for i in range(start, len(lines)):
        if _looks_like_heading(lines[i]):
            break
        collected.append(lines[i])
        if len(" ".join(collected)) > max_chars:
            break
        if not lines[i]:
            break
    return " ".join(collected)[:max_chars]


def _looks_like_heading(text: str) -> bool:
    if len(text.split()) > 12:
        return False
    if text.isupper():
        return True
    if text.startswith(tuple("0123456789")):
        return True
    if text.lower().startswith(tuple(LANG_HEADING_KEYWORDS["en"])):
        return True
    return False


def _is_abstract_heading(text: str) -> bool:
    candidates = (
        "abstract",
        "summary",
        "概要",
        "要旨",
        "摘要",
    )
    lower = text.lower()
    return any(lower.startswith(c) for c in candidates)


def _detect_language(lines: list[str]) -> str:
    sample = " ".join(lines[:10])
    if any("概要" in line or "要旨" in line for line in lines[:5]):
        return "ja"
    if any("摘要" in line for line in lines[:5]):
        return "zh"
    if re.search(r"[\u4e00-\u9fff]", sample):
        return "zh"
    return "en"


def extract_year_candidate_from_text(text: str) -> Optional[str]:
    match = re.search(r"(19|20)\d{2}", text)
    return match.group(0) if match else None


def extract_year_candidate(path: str | Path) -> Optional[str]:
    return extract_year_candidate_from_text(extract_plain_text(path))


def extract_authors_candidate_from_text(text: str, max_len: int = 160) -> str:
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines[:8]:
        if _looks_like_heading(line):
            continue
        if len(line.split()) <= 2 and line.replace(" ", "").isalpha():
            return line[:max_len]
        if any(sep in line for sep in (",", " and ", "・")):
            return line[:max_len]
    return lines[0][:max_len] if lines else ""


def extract_authors_candidate(path: str | Path, max_len: int = 160) -> str:
    return extract_authors_candidate_from_text(extract_plain_text(path), max_len)
