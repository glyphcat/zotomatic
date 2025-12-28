"""pipelines"""

import threading
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from zotomatic import config
from zotomatic.llm import create_llm_client
from zotomatic.logging import get_logger
from zotomatic.note import (
    NoteBuilder,
    NoteBuilderConfig,
    NoteBuilderContext,
    NoteWorkflowConfig,
    NoteWorkflowContext,
    NoteWorkflow,
)
from zotomatic.repositories import (
    NoteRepository,
    PDFRepository,
    WatcherStateRepositoryConfig,
)
from zotomatic.repositories.watcher_state import WatcherStateRepository
from zotomatic.services import (
    PendingQueue,
    PendingQueueProcessor,
    PendingQueueProcessorConfig,
    ZoteroResolver,
)
from zotomatic.watcher import PDFStorageWatcher, WatcherConfig
from zotomatic.zotero import ZoteroClient, ZoteroClientConfig


def _merge_config(cli_options: Mapping[str, Any] | None) -> dict[str, Any]:
    return config.get_config(cli_options or {})




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
    pending_processor_config = PendingQueueProcessorConfig()
    seed_batch_limit = pending_processor_config.batch_limit
    pending_seed_buffer: list[Path] = []
    pending_seed_lock = threading.Lock()
    runtime_seed_complete = False
    boot_seed_complete = state_repository.meta.get("boot_seed_complete") == "1"
    stop_event = threading.Event()
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

    note_workflow = NoteWorkflow(
        note_builder=note_builder,
        note_repository=note_repository,
        llm_client=llm_client,
        config=NoteWorkflowConfig(
            summary_enabled=summary_enabled,
            tag_enabled=tag_enabled,
            summary_mode=summary_mode,
        ),
        logger=logger,
    )

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
                if note_workflow.update_pdf_path_if_changed(
                    NoteWorkflowContext(
                        builder_context=context,
                        existing_path=existing,
                    )
                ):
                    return
                if note_workflow.update_pending_note(
                    NoteWorkflowContext(
                        builder_context=context,
                        existing_path=existing,
                    )
                ):
                    return
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

        # ノート生成
        note = note_workflow.create_new_note(
            NoteWorkflowContext(builder_context=context)
        )
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

    zotero_resolver = ZoteroResolver.from_state_repository(
        client=zotero_client,
        state_repository=state_repository,
    )
    pending_processor = PendingQueueProcessor(
        queue=pending_queue,
        zotero_resolver=zotero_resolver,
        on_resolved=_process_pdf,
        config=pending_processor_config,
        stop_event=stop_event,
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
                    logger.info(
                        "Pending queue processor processed %s item(s).", processed
                    )
                if stop_event.wait(pending_processor.loop_interval_seconds):
                    break
        except KeyboardInterrupt:
            stop_event.set()
            logger.info("Stopping watcher at user request")

    logger.info("Watcher stopped (ready mode).")

    if llm_client:
        llm_client.close()

    return 0


def run_init(cli_options: Mapping[str, Any] | None = None):
    """Init command."""
    logger = get_logger("zotomatic.init", False)
    cli_options = dict(cli_options or {})
    if not cli_options.get("pdf_dir"):
        logger.error("Missing required option: --pdf-dir")
        return
    init_result = config.initialize_config(cli_options)
    settings = config.get_config(cli_options)

    if init_result.config_created:
        logger.info("Config created at %s", init_result.config_path)
    elif init_result.config_updated_keys:
        logger.info(
            "Config updated at %s (added: %s)",
            init_result.config_path,
            ", ".join(init_result.config_updated_keys),
        )
    else:
        logger.info("Config already exists at %s", init_result.config_path)

    if init_result.template_created:
        logger.info("Template created at %s", init_result.template_path)
    else:
        logger.info("Template already exists at %s", init_result.template_path)

    db_config = WatcherStateRepositoryConfig.from_settings(settings)
    db_path = db_config.sqlite_path.expanduser()
    db_exists = db_path.exists()
    try:
        _ = WatcherStateRepository.from_settings(settings)
    except Exception as exc:  # pragma: no cover - sqlite/filesystem dependent
        logger.error("Failed to initialize DB at %s: %s", db_path, exc)
        return

    if db_exists:
        logger.info("DB already exists at %s", db_path)
    else:
        logger.info("DB initialized at %s", db_path)


def stub_run_backfill(cli_options: Mapping[str, Any] | None = None): ...


def stub_run_doctor(cli_options: Mapping[str, Any] | None = None): ...


def run_template_create(cli_options: Mapping[str, Any] | None = None):
    logger = get_logger("zotomatic.template", False)
    cli_options = dict(cli_options or {})
    template_path = cli_options.get("template_path")
    if not template_path:
        logger.error("Missing required option: --path")
        return

    init_result = config.initialize_config(cli_options)
    updated = config.update_config_value(
        init_result.config_path, "template_path", template_path
    )

    template_target = Path(str(template_path)).expanduser()
    if template_target.exists():
        logger.info("Template already exists at %s", template_target)
    else:
        template_target.parent.mkdir(parents=True, exist_ok=True)
        source_template = Path(__file__).resolve().parent / "templates" / "note.md"
        if not source_template.is_file():
            logger.error("Default template not found: %s", source_template)
            return
        template_target.write_text(
            source_template.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        logger.info("Template created at %s", template_target)

    if updated:
        logger.info("Config updated: template_path=%s", template_target)
    else:
        logger.info("Config already set: template_path=%s", template_target)


def run_template_set(cli_options: Mapping[str, Any] | None = None):
    logger = get_logger("zotomatic.template", False)
    cli_options = dict(cli_options or {})
    template_path = cli_options.get("template_path")
    if not template_path:
        logger.error("Missing required option: --path")
        return

    init_result = config.initialize_config(cli_options)
    updated = config.update_config_value(
        init_result.config_path, "template_path", template_path
    )
    template_target = Path(str(template_path)).expanduser()
    if not template_target.exists():
        logger.warning("Template not found at %s", template_target)
    if updated:
        logger.info("Config updated: template_path=%s", template_target)
    else:
        logger.info("Config already set: template_path=%s", template_target)
