"""pipelines"""

import threading
import time
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import zotomatic
from zotomatic import config
from zotomatic.llm import (
    BaseLLMClient,
    LLMSummaryContext,
    LLMTagsContext,
    create_llm_client,
)
from zotomatic.logging import get_logger
from zotomatic.note import NoteBuilder, NoteBuilderConfig, NoteBuilderContext
from zotomatic.repositories import NoteRepository, PDFRepository
from zotomatic.repositories.watcher_state import WatcherStateRepository
from zotomatic.services import (
    PendingQueue,
    PendingQueueProcessor,
    PendingQueueProcessorConfig,
)
from zotomatic.watcher import PDFStorageWatcher, WatcherConfig
from zotomatic.zotero import ZoteroClient, ZoteroClientConfig


def _merge_config(cli_options: Mapping[str, Any] | None) -> dict[str, Any]:
    return config.get_config(cli_options or {})


def _maybe_generate_summary(
    context: NoteBuilderContext,
    llm_client: BaseLLMClient | None,
    summary_enabled: bool,
    summary_mode: str,
    logger,
):
    normalized_mode = summary_mode or "quick"
    if summary_enabled and llm_client:
        try:
            summary_context = LLMSummaryContext.from_note_builder_context(
                context, mode=normalized_mode
            )
            summary_result = llm_client.generate_summary(summary_context)
            summary_text = (summary_result.summary or "").strip()
            if summary_result and summary_text:
                context = context.with_updates(
                    generated_summary=summary_text,
                    zotomatic_summary_status="done",
                    zotomatic_summary_mode=normalized_mode,
                )
        except NotImplementedError:  # pragma: no cover - base stub
            logger.debug("LLM summary not implemented; leaving status pending")
        except Exception:  # pragma: no cover
            logger.exception("Summary generation failed; leaving status pending")
    elif not summary_enabled:
        context = context.with_updates(
            zotomatic_summary_status="pending",
            zotomatic_summary_mode="",
        )
    else:
        context = context.with_updates(zotomatic_summary_mode=normalized_mode)
    return context


def _maybe_generate_tags(
    context: NoteBuilderContext,
    llm_client: BaseLLMClient | None,
    tag_enabled: bool,
    logger,
):
    if tag_enabled and llm_client:
        try:
            tag_context = LLMTagsContext.from_note_builder_context(context)
            tag_result = llm_client.generate_tags(tag_context)
            if tag_result and tag_result.tags:
                context = context.with_updates(
                    generated_tags=tag_result.tags,
                    zotomatic_tag_status="done",
                )
        except NotImplementedError:  # pragma: no cover
            logger.debug("LLM tagging not implemented; leaving status pending")
        except Exception:  # pragma: no cover
            logger.exception("Tag generation failed; leaving status pending")
    elif not tag_enabled:
        context = context.with_updates(zotomatic_tag_status="pending")
    return context


# def _apply_ai_enrichments(
#     context: NoteBuilderContext,
#     llm_client: BaseLLMClient | None,
#     summary_enabled: bool,
#     tag_enabled: bool,
#     logger,
# ) -> NoteBuilderContext:
#     summary_status = context.zotomatic_summary_status
#     tag_status = context.zotomatic_tag_status
#     generated_tags = context.generated_tags

#     if summary_enabled and llm_client:
#         try:
#             summary_context = LLMSummaryContext.from_note_builder_context(context)
#             summary_result = llm_client.generate_summary(summary_context)
#             if summary_result:
#                 context = context.with_updates(
#                     abstract=summary_result.summary or context.abstract,
#                     key_points=context.key_points,
#                     highlights=context.highlights,
#                 )
#                 summary_status = "done"
#         except NotImplementedError:  # pragma: no cover - base stub
#             logger.debug("LLM summary not implemented; leaving status pending")
#         except Exception:  # pragma: no cover
#             logger.exception("Summary generation failed; leaving status pending")
#     elif not summary_enabled:
#         summary_status = "pending"

#     if tag_enabled and llm_client:
#         try:
#             tag_context = LLMTagsContext.from_note_builder_context(context)
#             tag_result = llm_client.generate_tags(tag_context)
#             if tag_result and tag_result.tags:
#                 merged = list(generated_tags)
#                 for tag in tag_result.tags:
#                     tag_str = str(tag).strip()
#                     if tag_str and tag_str not in merged:
#                         merged.append(tag_str)
#                 generated_tags = tuple(merged)
#                 tag_status = "done"
#         except NotImplementedError:  # pragma: no cover
#             logger.debug("LLM tagging not implemented; leaving status pending")
#         except Exception:  # pragma: no cover
#             logger.exception("Tag generation failed; leaving status pending")
#     elif not tag_enabled:
#         tag_status = "pending"

#     return context.with_updates(
#         generated_tags=generated_tags,
#         zotomatic_summary_status=summary_status,
#         zotomatic_tag_status=tag_status,
#     )


def run_ready(cli_options: Mapping[str, Any] | None = None):
    """
    Ready command
    """

    # Zotomaticのユーザー設定取得
    settings = _merge_config(cli_options)

    # repositoryの準備
    note_repository = NoteRepository.from_settings(settings)
    pdf_repository = PDFRepository.from_settings(settings)
    state_repository = WatcherStateRepository.from_settings(settings)
    pending_queue = PendingQueue.from_state_repository(state_repository)
    pending_processor_config = PendingQueueProcessorConfig.from_settings(settings)
    seed_batch_limit = pending_processor_config.batch_limit
    pending_seed_buffer: list[Path] = []
    pending_seed_lock = threading.Lock()
    runtime_seed_complete = False
    boot_seed_complete = state_repository.meta.get("boot_seed_complete") == "1"
    citekey_index = note_repository.build_citekey_index()
    note_builder = NoteBuilder(
        repository=note_repository,
        config=NoteBuilderConfig.from_settings(settings),
    )
    zotero_client = ZoteroClient(config=ZoteroClientConfig.from_settings(settings))

    # LLMによる自動生成の設定値
    summary_enabled = bool(settings.get("llm_summary_enabled", True))
    tag_enabled = bool(settings.get("llm_tag_enabled", True))
    summary_mode = str(settings.get("llm_summary_mode", "quick") or "quick")

    # LLMClient生成
    logger = get_logger("zotomatic.ready", settings.get("watch_verbose_logging", False))
    try:
        llm_client = create_llm_client(settings)
    except ValueError as exc:
        logger.info("LLM client disabled: %s", exc)
        llm_client = None

    def _process_pdf(pdf_path: Path) -> None:
        pdf_path = Path(pdf_path)
        _ = pdf_repository  # placeholder for future PDF operations

        context = zotero_client.build_context(pdf_path) or NoteBuilderContext(
            title=pdf_path.stem,
            pdf_path=str(pdf_path),
        )

        citekey = context.citekey
        if citekey:
            existing = citekey_index.get(citekey) or note_repository.find_by_citekey(
                citekey
            )
            if existing:
                logger.info(
                    "Note already exists for citekey=%s at %s; skipping.",
                    citekey,
                    existing,
                )
                return

        # context = _apply_ai_enrichments(
        #     base_context,
        #     llm_client,
        #     summary_enabled,
        #     tag_enabled,
        #     logger,
        # ).with_updates(
        #     zotomatic_last_updated=datetime.now(timezone.utc).isoformat(),
        # )

        # LLMによる要約生成
        context = _maybe_generate_summary(
            context,
            llm_client,
            summary_enabled,
            summary_mode,
            logger,
        )
        # LLMによるタグ生成
        context = _maybe_generate_tags(
            context,
            llm_client,
            tag_enabled,
            logger,
        )
        context = context.with_updates(
            zotomatic_last_updated=datetime.now(timezone.utc).isoformat(),
        )

        # ノート生成
        note = note_builder.generate_note(context=context)
        if citekey:
            citekey_index[citekey] = note.path
            logger.info("Generated note for citekey=%s -> %s", citekey, note.path)
        else:
            logger.info("Generated note -> %s", note.path)

    # TODO: 見づらいから外に出す？
    def _on_pdf_created(pdf_path):
        logger.debug("Watcher detected %s", pdf_path)
        pdf_path = Path(pdf_path)
        if boot_seed_complete:
            pending_queue.enqueue(pdf_path)
            return
        with pending_seed_lock:
            pending_seed_buffer.append(pdf_path)

    def _on_initial_scan_complete() -> None:
        nonlocal runtime_seed_complete
        runtime_seed_complete = True

    # watcherコンテキストの生成
    watcher_config = WatcherConfig.from_settings(
        settings,
        _on_pdf_created,
        state_repository=state_repository,
        on_initial_scan_complete=_on_initial_scan_complete,
    )

    pending_processor = PendingQueueProcessor(
        queue=pending_queue,
        zotero_client=zotero_client,
        on_resolved=_process_pdf,
        config=pending_processor_config,
    )

    # watcher起動
    logger.info("Starting watcher (ready mode)...")
    with PDFStorageWatcher(watcher_config):
        logger.info(
            "Watcher is running; placeholder logic keeps process alive briefly."
        )
        try:
            while True:
                if not boot_seed_complete:
                    with pending_seed_lock:
                        seed_batch = pending_seed_buffer[:seed_batch_limit]
                        del pending_seed_buffer[:seed_batch_limit]
                    for path in seed_batch:
                        pending_queue.enqueue(path)
                    if runtime_seed_complete and not pending_seed_buffer:
                        state_repository.meta.set("boot_seed_complete", "1")
                        boot_seed_complete = True
                        logger.info("Boot seed completed for pending queue.")

                processed = pending_processor.run_once()
                if processed:
                    logger.info("Pending resolver processed %s item(s).", processed)
                time.sleep(pending_processor.loop_interval_seconds)
        except KeyboardInterrupt:
            logger.info("Stopping watcher at user request")

    logger.info("Watcher stopped (ready mode).")

    if llm_client:
        llm_client.close()

    return 0


def run_init(cli_options: Mapping[str, Any] | None = None):
    """Init command."""
    config_path = config.initialize_config()
    logger = get_logger("zotomatic.init", False)
    logger.info("Config initialized at %s", config_path)


def stub_run_backfill(cli_options: Mapping[str, Any] | None = None): ...


def stub_run_doctor(cli_options: Mapping[str, Any] | None = None): ...
