from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from zotomatic.llm import BaseLLMClient, LLMSummaryContext, LLMTagsContext
from zotomatic.note.builder import NoteBuilder
from zotomatic.note.types import (
    Note,
    NoteBuilderContext,
    NoteWorkflowConfig,
    NoteWorkflowContext,
)
from zotomatic.note.updater import NoteUpdater
from zotomatic.repositories import NoteRepository
from zotomatic.utils.note import extract_summary_block, parse_frontmatter, parse_tags


class NoteWorkflow:
    """ノート生成/更新のワークフローをまとめる。"""

    def __init__(
        self,
        note_builder: NoteBuilder,
        note_repository: NoteRepository,
        llm_client: BaseLLMClient | None,
        config: NoteWorkflowConfig,
        logger,
    ) -> None:
        self._note_builder = note_builder
        self._note_repository = note_repository
        self._llm_client = llm_client
        self._summary_enabled = config.summary_enabled
        self._tag_enabled = config.tag_enabled
        self._summary_mode = config.summary_mode or "quick"
        self._logger = logger
        self._note_updater = NoteUpdater(note_builder=note_builder, logger=logger)

    def create_new_note(self, context: NoteWorkflowContext) -> Note:
        enriched = self._apply_ai(context.builder_context)
        return self._note_builder.generate_note(context=enriched)

    def update_pending_note(self, context: NoteWorkflowContext) -> bool:
        existing = context.existing_path
        if existing is None:
            raise ValueError("existing_path is required for pending updates.")
        try:
            text = existing.read_text(encoding=self._note_repository.config.encoding)
        except OSError:
            text = ""
        meta = parse_frontmatter(text)
        summary_status = str(meta.get("zotomatic_summary_status", "pending")).strip()
        tag_status = str(meta.get("zotomatic_tag_status", "pending")).strip()
        summary_should_regen = self._summary_enabled and summary_status == "pending"
        tag_should_regen = self._tag_enabled and tag_status == "pending"

        if not summary_should_regen and not tag_should_regen:
            return False

        builder_context = context.builder_context
        if not summary_should_regen:
            builder_context = builder_context.with_updates(
                generated_summary=extract_summary_block(text),
                zotomatic_summary_status=summary_status,
                zotomatic_summary_mode=str(meta.get("zotomatic_summary_mode", "")),
            )
        if not tag_should_regen:
            tags = parse_tags(str(meta.get("tags", "")))
            builder_context = builder_context.with_updates(
                tags=tags,
                zotomatic_tag_status=tag_status,
            )
        if summary_should_regen:
            builder_context = self._maybe_generate_summary(builder_context)
        if tag_should_regen:
            builder_context = self._maybe_generate_tags(builder_context)

        builder_context = builder_context.with_updates(
            zotomatic_last_updated=datetime.now(timezone.utc).isoformat(),
        )
        self._note_updater.update_existing(context=builder_context, existing=existing)
        return True

    def _apply_ai(self, context: NoteBuilderContext) -> NoteBuilderContext:
        context = self._maybe_generate_summary(context)
        context = self._maybe_generate_tags(context)
        return context.with_updates(
            zotomatic_last_updated=datetime.now(timezone.utc).isoformat(),
        )

    def _maybe_generate_summary(
        self, context: NoteBuilderContext
    ) -> NoteBuilderContext:
        if self._summary_enabled and self._llm_client:
            try:
                summary_context = LLMSummaryContext.from_note_builder_context(
                    context, mode=self._summary_mode
                )
                summary_result = self._llm_client.generate_summary(summary_context)
                summary_text = (summary_result.summary or "").strip()
                if summary_result and summary_text:
                    return context.with_updates(
                        generated_summary=summary_text,
                        zotomatic_summary_status="done",
                        zotomatic_summary_mode=self._summary_mode,
                    )
            except NotImplementedError:  # pragma: no cover
                self._logger.debug(
                    "LLM summary not implemented; leaving status pending"
                )
            except Exception:  # pragma: no cover
                self._logger.exception(
                    "Summary generation failed; leaving status pending"
                )
        elif not self._summary_enabled:
            return context.with_updates(
                zotomatic_summary_status="pending",
                zotomatic_summary_mode="",
            )
        else:
            return context.with_updates(zotomatic_summary_mode=self._summary_mode)
        return context

    def _maybe_generate_tags(self, context: NoteBuilderContext) -> NoteBuilderContext:
        if self._tag_enabled and self._llm_client:
            try:
                tag_context = LLMTagsContext.from_note_builder_context(context)
                tag_result = self._llm_client.generate_tags(tag_context)
                if tag_result and tag_result.tags:
                    return context.with_updates(
                        generated_tags=tag_result.tags,
                        zotomatic_tag_status="done",
                    )
            except NotImplementedError:  # pragma: no cover
                self._logger.debug(
                    "LLM tagging not implemented; leaving status pending"
                )
            except Exception:  # pragma: no cover
                self._logger.exception("Tag generation failed; leaving status pending")
        elif not self._tag_enabled:
            return context.with_updates(zotomatic_tag_status="pending")
        return context
