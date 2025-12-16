from dataclasses import dataclass, replace
from typing import Optional


@dataclass(frozen=True, slots=True)
class ZoteroAnnotation:
    pageLabel: Optional[str]
    text: str
    comment: Optional[str]


# Zoteroメタデータ
@dataclass(frozen=True, slots=True)
class ZoteroPaper:
    key: str
    citekey: Optional[str]
    title: str
    year: Optional[str]
    authors: str
    publicationTitle: Optional[str]
    DOI: Optional[str]
    url: Optional[str]
    abstractNote: Optional[str]
    collections: list[str]
    zoteroSelectURI: str
    filePath: str
    annotations: list[ZoteroAnnotation]

    def update(self, **kwargs: object) -> "ZoteroPaper":
        return replace(self, **kwargs)


@dataclass(frozen=True, slots=True)
class ZoteroClientConfig:
    """Connection parameters for the Zotero client."""

    library_id: str
    library_type: str = "user"
    api_key: str = ""

    @property
    def enabled(self) -> bool:
        return bool(self.library_id and self.api_key)

    @classmethod
    def from_settings(cls, settings: dict[str, object]) -> "ZoteroClientConfig":
        return cls(
            library_id=str(settings.get("zotero_library_id") or ""),
            library_type=str(settings.get("zotero_library_scope") or "user"),
            api_key=str(settings.get("zotero_api_token") or ""),
        )
