import re
from typing import Iterable, Optional

from zotomatic.zotero.types import ZoteroAnnotation, ZoteroPaper


def authors_str(creators) -> str:
    names = []
    for c in creators or []:
        if "lastName" in c and "firstName" in c:
            names.append(f"{c['firstName']} {c['lastName']}")
        elif "name" in c:
            names.append(c["name"])
    return ", ".join(names)


def extract_year(date_str: str) -> Optional[str]:
    if not date_str:
        return None
    m = re.search(r"\d{4}", date_str)
    return m.group(0) if m else None


def render_annotations(annotations: Iterable[ZoteroAnnotation]) -> str:
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


def derive_source_url(paper: ZoteroPaper) -> str:
    if paper.url:
        return paper.url
    if paper.DOI:
        return f"https://doi.org/{paper.DOI}"
    return ""
