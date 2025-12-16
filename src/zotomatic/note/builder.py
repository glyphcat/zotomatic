import re
import unicodedata
from pathlib import Path
from typing import Any, Mapping

from zotomatic.errors import NoteRepositoryError
from zotomatic.note.types import Note, NoteBuilderConfig, NoteBuilderContext
from zotomatic.repositories import NoteRepository
from zotomatic.utils import slug

_FILENAME_TOKEN = re.compile(r"\{\{\s*(\w+)\s*\}\}")


class NoteBuilder:
    """テンプレートを用いたノート生成."""

    def __init__(
        self,
        repository: NoteRepository,
        config: NoteBuilderConfig | None = None,
    ) -> None:
        self._repository = repository
        if config is None:
            raise ValueError("NoteBuilderConfig must be provided for NoteBuilder.")
        self._config = config
        self._template_cache: str | None = None

    # TODO: apiの実装に備えてnote生成をコンテキストに依存せずに行えるようにする
    # TODO: 純粋なノート生成処理と論文PDFからのノート生成は分けて考えてcitekeyなどに依存せず動けるようにする？

    def generate_note(
        self,
        context: NoteBuilderContext,
        relative_path: str | Path | None = None,
    ) -> Note:
        """コンテキストをテンプレートへ差し込みノートを生成する."""

        prepared_context = self._prepare_context(context)
        rendered = self._render_from_prepared(prepared_context)
        output_path = relative_path or self._build_output_path(prepared_context)
        path = self._repository.write(output_path, rendered)
        citekey = prepared_context.get("citekey")
        if citekey:
            self._repository.add_to_index(citekey, path)
        return Note(
            path=path,
            content=rendered,
            context=context,
            rendered_context=prepared_context,
        )

    # TODO: render()について使用しないなら削除する。
    def render(self, context: NoteBuilderContext | Mapping[str, Any]) -> str:
        """テンプレートへデータを埋め込みMarkdown文字列を返す."""

        if isinstance(context, NoteBuilderContext):
            prepared_context = self._prepare_context(context)
        else:
            prepared_context = self._prepare_context(
                NoteBuilderContext.from_mapping(context)
            )
        return self._render_from_prepared(prepared_context)

    def _render_from_prepared(self, prepared_context: dict[str, Any]) -> str:
        template = self._load_template()
        try:
            return template.format(**prepared_context)
        except KeyError as exc:  # pragma: no cover - depends on template edits
            missing_key = exc.args[0]
            raise NoteRepositoryError(
                f"Template placeholder '{missing_key}' is missing from context."
            ) from exc

    def _load_template(self) -> str:
        if self._template_cache is not None:
            return self._template_cache
        try:
            template_text = self._config.template_path.read_text(encoding="utf-8")
        except OSError as exc:  # pragma: no cover - filesystem dependent
            raise NoteRepositoryError(
                f"Failed to load note template: {self._config.template_path}"
            ) from exc
        self._template_cache = template_text
        return template_text

    def _prepare_context(self, context: NoteBuilderContext) -> dict[str, Any]:
        # 既存タグと生成されたタグのマージ
        tags_source = list(context.tags) + list(context.generated_tags)
        tags_list: list[str] = []
        for tag in tags_source:
            tag_str = _normalize_tag_value(str(tag))
            if tag_str and tag_str not in tags_list:
                tags_list.append(tag_str)

        year = context.year or ""
        default_tags = ["paper"]
        if year:
            default_tags.append(f"y{year}")
        for tag in default_tags:
            if tag not in tags_list:
                tags_list.append(tag)

        tags_str = ", ".join(tags_list)

        title = context.title or "(untitled)"
        citekey = context.citekey or ""

        prepared: dict[str, Any] = {
            "title": title,
            "citekey": citekey,
            "year": year,
            "authors": context.authors or "",
            "venue": context.venue or "",
            "doi": context.doi or "",
            "url": context.url or "",
            "source_url": context.source_url or "",
            "zotero_select_uri": context.zotero_select_uri or "",
            "pdf_path": context.pdf_path or "",
            "tags": tags_str,
            "tags_list": tags_list,
            "abstract": context.abstract or "",
            "generated_summary": context.generated_summary or "",
            "key_points": context.key_points or "-",
            "highlights": context.highlights or "",
            "zotomatic_summary_status": context.zotomatic_summary_status or "pending",
            "zotomatic_summary_mode": context.zotomatic_summary_mode or "",
            "zotomatic_tag_status": context.zotomatic_tag_status or "pending",
            "zotomatic_last_updated": context.zotomatic_last_updated or "",
        }

        slug_source = title or citekey or year or "note"
        prepared["slug80"] = slug.slugify(slug_source, max_length=80)
        prepared["slug40"] = slug.slugify(slug_source, max_length=40)

        return prepared

    def _build_output_path(self, prepared_context: dict[str, Any]) -> Path:
        pattern = self._config.filename_pattern
        rendered = _render_filename_pattern(pattern, prepared_context).strip()
        if not rendered:
            rendered = prepared_context.get("slug80", "note") or "note"

        candidate = Path(rendered)
        if candidate.suffix:
            return candidate
        return candidate.with_suffix(".md")


# md生成
def stub_generate_note(): ...


# 要約挿入
def stub_insert_summary(): ...


# tag挿入
def stub_insert_tags(): ...


def _render_filename_pattern(pattern: str, context: dict[str, Any]) -> str:
    def replacer(match: re.Match[str]) -> str:
        key = match.group(1)
        return str(context.get(key, ""))

    return _FILENAME_TOKEN.sub(replacer, pattern)


def _normalize_tag_value(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        return ""
    return re.sub(r"\s+", "-", normalized)
