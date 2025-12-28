from __future__ import annotations

from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Any, Mapping

from zotomatic.errors import ZotomaticMissingSettingError


@dataclass(frozen=True, slots=True)
class NoteBuilderConfig:
    """Note Builder の設定値."""

    template_path: Path
    filename_pattern: str

    def __post_init__(self) -> None:  # type: ignore[override]
        object.__setattr__(self, "template_path", Path(self.template_path).expanduser())

    @classmethod
    def from_settings(
        cls, settings: Mapping[str, Any] | None = None
    ) -> "NoteBuilderConfig":
        settings = settings or {}
        template_path = settings.get("template_path")
        if not template_path:
            raise ZotomaticMissingSettingError("template_path")

        filename_pattern = settings.get("note_title_pattern")
        if not filename_pattern:
            raise ZotomaticMissingSettingError("note_title_pattern")

        return cls(Path(template_path), filename_pattern)


@dataclass(frozen=True, slots=True)
class NoteWorkflowConfig:
    """Note Workflow の設定値."""

    summary_enabled: bool = True
    tag_enabled: bool = True
    summary_mode: str = "quick"


# TODO: Note -> NoteResultにリネーム. frozen=Trueにするか検討する.
@dataclass(slots=True)
class Note:
    """生成結果を保持する簡易データクラス."""

    path: Path
    content: str
    context: "NoteBuilderContext"
    rendered_context: dict[str, Any]


@dataclass(frozen=True, slots=True)
class NoteBuilderContext:
    """ノート生成に必要な値を束ねるコンテナ。"""

    title: str = ""
    citekey: str = ""
    year: str = ""
    authors: str = ""
    venue: str = ""
    doi: str = ""
    url: str = ""
    source_url: str = ""
    zotero_select_uri: str = ""
    pdf_path: str = ""
    tags: tuple[str, ...] = ()
    generated_tags: tuple[str, ...] = ()
    abstract: str = ""
    generated_summary: str = ""
    highlights: str = ""
    zotomatic_summary_status: str = "pending"
    zotomatic_tag_status: str = "pending"
    zotomatic_last_updated: str = ""
    zotomatic_summary_mode: str = ""

    def __post_init__(self) -> None:  # type: ignore[override]
        object.__setattr__(self, "tags", tuple(self.tags))
        object.__setattr__(self, "generated_tags", tuple(self.generated_tags))

    @classmethod
    def empty(cls) -> NoteBuilderContext:
        return cls()

    # TODO: NoteBuilderのrender()について使用しないならfrom_mappingも不要なので削除する
    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> NoteBuilderContext:
        allowed = {f.name for f in fields(cls)}
        filtered = {k: data[k] for k in data if k in allowed}
        return cls(**filtered)

    def with_updates(self, **overrides: Any) -> NoteBuilderContext:
        return replace(self, **overrides)


@dataclass(frozen=True, slots=True)
class NoteWorkflowContext:
    """ワークフローで扱うノート生成/更新の入力."""

    builder_context: NoteBuilderContext
    existing_path: Path | None = None
