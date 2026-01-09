"""pipelines"""

import os
import subprocess
import sys
import threading
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pyzotero import zotero

from zotomatic import config
from zotomatic.errors import ZotomaticCLIError, ZotomaticLLMConfigError
from zotomatic.llm import create_llm_client
from zotomatic.llm.types import LLM_PROVIDER_DEFAULTS
from zotomatic.logging import get_logger
from zotomatic.note.builder import NoteBuilder
from zotomatic.note.types import (
    NoteBuilderConfig,
    NoteBuilderContext,
    NoteWorkflowConfig,
    NoteWorkflowContext,
)
from zotomatic.note.workflow import NoteWorkflow
from zotomatic.repositories import (
    LLMUsageRepository,
    NoteRepository,
    PDFRepository,
    WatcherStateRepositoryConfig,
)
from zotomatic.repositories.watcher_state import WatcherStateRepository
from zotomatic.services import (
    LLMUsageService,
    PendingQueue,
    PendingQueueProcessor,
    PendingQueueProcessorConfig,
    ZoteroResolver,
)
from zotomatic.watcher import PDFStorageWatcher, WatcherConfig
from zotomatic.zotero import ZoteroClient, ZoteroClientConfig


def _merge_config(cli_options: Mapping[str, Any] | None) -> dict[str, Any]:
    return config.get_config(cli_options or {})


def run_scan(cli_options: Mapping[str, Any] | None = None):
    """Scan command."""

    # Zotomaticのユーザー設定取得
    cli_options = dict(cli_options or {})
    scan_paths = cli_options.pop("path", None)
    scan_once = bool(cli_options.pop("once", False))
    scan_watch = bool(cli_options.pop("watch", False))
    scan_force = bool(cli_options.pop("force", False))
    scan_modes = sum([bool(scan_paths), scan_once, scan_watch])
    if scan_modes > 1:
        raise ZotomaticCLIError(
            "Scan options are mutually exclusive: --once, --watch, --path"
        )
    if scan_paths and scan_force:
        raise ZotomaticCLIError("--force cannot be used with --path")
    if not scan_paths and not scan_once and not scan_watch:
        scan_once = True
    scan_mode = "path" if scan_paths else ("once" if scan_once else "watch")
    scan_mode_label = scan_mode
    if scan_force and scan_mode in {"once", "watch"}:
        scan_mode_label = f"{scan_mode}, force"
    settings = _merge_config(cli_options)

    # repositoryの準備
    note_repository = NoteRepository.from_settings(settings)
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
    logger = get_logger("zotomatic.scan", settings.get("watch_verbose_logging", False))
    try:
        llm_client = create_llm_client(settings)
    except ZotomaticLLMConfigError:
        llm_client = None

    llm_usage = LLMUsageService(
        repository=LLMUsageRepository.from_settings(settings),
        daily_limit=settings.get("llm_daily_limit"),
        logger=logger,
    )
    llm_limit_notified = False

    def _notify_llm_limit_reached() -> None:
        nonlocal llm_limit_notified
        if llm_limit_notified:
            return
        if not llm_client or not (summary_enabled or tag_enabled):
            return
        limit = llm_usage.daily_limit
        if not limit or limit <= 0:
            return
        used = llm_usage.get_total_used()
        if used >= limit:
            print(
                "LLM daily limit reached; summaries/tags will be skipped for remaining PDFs."
            )
            llm_limit_notified = True

    def _should_note_llm_limit() -> bool:
        if not llm_client or not (summary_enabled or tag_enabled):
            return False
        limit = llm_usage.daily_limit
        if not limit or limit <= 0:
            return False
        return llm_usage.get_total_used() >= limit

    note_workflow = NoteWorkflow(
        note_builder=note_builder,
        note_repository=note_repository,
        llm_client=llm_client,
        config=NoteWorkflowConfig(
            summary_enabled=summary_enabled,
            tag_enabled=tag_enabled,
            summary_mode=summary_mode,
        ),
        llm_usage=llm_usage,
        logger=logger,
    )

    created_count = 0
    updated_count = 0
    skipped_count = 0
    error_count = 0
    error_paths: list[Path] = []

    def _process_pdf(pdf_path: Path) -> None:
        nonlocal created_count, updated_count, skipped_count
        pdf_path = Path(pdf_path)
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
                    updated_count += 1
                    _notify_llm_limit_reached()
                    return
                if note_workflow.update_pending_note(
                    NoteWorkflowContext(
                        builder_context=context,
                        existing_path=existing,
                    )
                ):
                    updated_count += 1
                    _notify_llm_limit_reached()
                    return
                logger.debug(
                    "Note already exists (citekey=%s): %s; skipping.",
                    citekey,
                    existing,
                )
                skipped_count += 1
                return

        # ノート生成
        note = note_workflow.create_new_note(
            NoteWorkflowContext(builder_context=context)
        )
        created_count += 1
        if citekey:
            citekey_index[citekey] = note.path
            print(f"Note created: {note.path}")
        else:
            print(f"Note created: {note.path}")
        _notify_llm_limit_reached()

    _notify_llm_limit_reached()

    def _process_pdf_safe(pdf_path: Path) -> None:
        nonlocal error_count
        try:
            _process_pdf(pdf_path)
        except Exception:  # pragma: no cover - depends on downstream failures
            error_count += 1
            error_paths.append(Path(pdf_path))
            logger.exception("Failed to process PDF: %s", pdf_path)
            raise

    if scan_paths:
        expanded_paths = [Path(path).expanduser() for path in scan_paths]
        invalid = [
            path
            for path in expanded_paths
            if not path.exists() or not path.is_file()
        ]
        if invalid:
            invalid_list = ", ".join(str(path) for path in invalid)
            raise ZotomaticCLIError(
                f"Invalid PDF path(s): {invalid_list}",
                hint="Pass existing PDF file paths to --path.",
            )
        print(f"Scan started ({scan_mode_label}).")
        for path in expanded_paths:
            try:
                _process_pdf_safe(path)
            except Exception:
                continue
        print(f"Scan completed ({scan_mode_label}).")
        print(
            f"Summary: created={created_count}, updated={updated_count}, "
            f"skipped={skipped_count}, pending=0, dropped=0, errors={error_count}"
        )
        if _should_note_llm_limit():
            print(
                "Note: LLM daily limit reached today; summaries/tags may be pending."
            )
        if error_paths:
            print("Errors:")
            for path in error_paths[:10]:
                print(f"  - {path}")
            if len(error_paths) > 10:
                print(f"  ... {len(error_paths) - 10} more")
            print("Hint: retry specific PDFs with `zotomatic scan --path <path>`")
        if llm_client:
            llm_client.close()
        return 0

    # pdf_repository = PDFRepository.from_settings(settings)
    state_repository = WatcherStateRepository.from_settings(settings)
    pending_queue = PendingQueue.from_state_repository(state_repository)
    pending_processor_config = PendingQueueProcessorConfig()
    seed_batch_limit = pending_processor_config.batch_limit
    pending_seed_buffer: list[Path] = []
    pending_seed_lock = threading.Lock()
    runtime_seed_complete = False
    boot_seed_complete = state_repository.meta.get("boot_seed_complete") == "1"
    initial_scan_announced = False
    initial_processing_announced = False
    initial_scan_started_at = time.perf_counter()
    stop_event = threading.Event()

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
        nonlocal initial_scan_announced
        runtime_seed_complete = True
        if not scan_once and not initial_scan_announced:
            elapsed = time.perf_counter() - initial_scan_started_at
            print(
                "Initial scan complete in "
                f"{elapsed:.2f}s. Processing queued PDFs... (press Ctrl+C to stop)"
            )
            initial_scan_announced = True

    # watcherコンテキストの生成
    watcher_config = WatcherConfig.from_settings(
        settings,
        _on_pdf_created,
        state_repository=state_repository,
        on_initial_scan_complete=_on_initial_scan_complete,
        force_scan=scan_force,
    )

    zotero_resolver = ZoteroResolver.from_state_repository(
        client=zotero_client,
        state_repository=state_repository,
    )
    pending_processor = PendingQueueProcessor(
        queue=pending_queue,
        zotero_resolver=zotero_resolver,
        on_resolved=_process_pdf_safe,
        config=pending_processor_config,
        stop_event=stop_event,
    )

    # watcher起動
    print(f"Scan started ({scan_mode_label}).")
    waiting_announced = False
    with PDFStorageWatcher(watcher_config) as watcher:
        logger.debug("Scan watcher running.")
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
                        logger.debug("Pending queue boot seed completed.")

                processed = pending_processor.run_once()
                if processed:
                    logger.debug("Pending queue processed %s item(s).", processed)
                    waiting_announced = False
                if (
                    not scan_once
                    and runtime_seed_complete
                    and boot_seed_complete
                    and not pending_seed_buffer
                    and not pending_queue.get_due(limit=1)
                ):
                    if not initial_processing_announced:
                        print("Initial processing complete.")
                        initial_processing_announced = True
                        print("Waiting for new PDFs...")
                        waiting_announced = True
                    elif not waiting_announced:
                        print("Waiting for new PDFs...")
                        waiting_announced = True
                if scan_once:
                    no_due = not pending_queue.get_due(limit=1)
                    if (
                        runtime_seed_complete
                        and boot_seed_complete
                        and not pending_seed_buffer
                        and no_due
                    ):
                        print("Scan completed.")
                        break
                    time.sleep(pending_processor.loop_interval_seconds)
                    continue
                if stop_event.wait(pending_processor.loop_interval_seconds):
                    break
        except KeyboardInterrupt:
            stop_event.set()
            logger.debug("Stopping scan watcher on user request.")

    print(f"Scan stopped ({scan_mode_label}).")
    total_skipped = skipped_count
    pending_count = pending_queue.count_all()
    dropped_count = pending_processor.dropped_count
    skipped_by_state = watcher.skipped_by_state
    print(
        f"Summary: created={created_count}, updated={updated_count}, "
        f"skipped={total_skipped}, pending={pending_count}, "
        f"dropped={dropped_count}, errors={error_count}"
    )
    pending_paths = pending_queue.list_all(limit=10)
    dropped_paths = pending_processor.dropped_paths[:10]
    if pending_paths:
        print("Pending:")
        for entry in pending_paths:
            print(f"  - {entry.file_path}")
        if pending_count > len(pending_paths):
            print(f"  ... {pending_count - len(pending_paths)} more")
    if dropped_paths:
        print("Dropped:")
        for path in dropped_paths:
            print(f"  - {path}")
        if dropped_count > len(dropped_paths):
            print(f"  ... {dropped_count - len(dropped_paths)} more")
    if error_paths:
        print("Errors:")
        for path in error_paths[:10]:
            print(f"  - {path}")
        if len(error_paths) > 10:
            print(f"  ... {len(error_paths) - 10} more")
    if pending_count or dropped_count or error_paths:
        print("Hint: retry specific PDFs with `zotomatic scan --path <path>`")
    if skipped_by_state:
        print(
            f"Note: {skipped_by_state} PDFs were unchanged (no processing needed)."
        )
    if _should_note_llm_limit():
        print("Note: LLM daily limit reached today; summaries/tags may be pending.")

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
        print(f"Config created: {init_result.config_path}")
    elif init_result.config_updated_keys:
        print(
            f"Config updated: {init_result.config_path} "
            f"(added: {', '.join(init_result.config_updated_keys)})"
        )
    else:
        print(f"Config exists: {init_result.config_path}")

    if init_result.template_created:
        print(f"Template created: {init_result.template_path}")
    else:
        print(f"Template exists: {init_result.template_path}")

    llm_provider = cli_options.get("llm_provider")
    if llm_provider:
        provider = str(llm_provider).strip().lower()
        if provider not in LLM_PROVIDER_DEFAULTS:
            logger.error("Unsupported LLM provider: %s", provider)
            return
        updated = config.update_config_section_value(
            init_result.config_path, "llm", "provider", provider
        )
        defaults = LLM_PROVIDER_DEFAULTS.get(provider, {})
        model = defaults.get("model")
        base_url = defaults.get("base_url")
        if model:
            config.update_config_section_value(
                init_result.config_path,
                f"llm.providers.{provider}",
                "model",
                model,
            )
        if base_url:
            config.update_config_section_value(
                init_result.config_path,
                f"llm.providers.{provider}",
                "base_url",
                base_url,
            )
        config.normalize_config(init_result.config_path)
        if updated:
            print(f"Config updated: llm.provider={provider}")
        else:
            print(f"Config exists: llm.provider={provider}")

    db_config = WatcherStateRepositoryConfig.from_settings(settings)
    db_path = db_config.sqlite_path.expanduser()
    db_exists = db_path.exists()
    try:
        _ = WatcherStateRepository.from_settings(settings)
    except Exception as exc:  # pragma: no cover - sqlite/filesystem dependent
        logger.error("Failed to initialize DB: %s (%s)", db_path, exc)
        return

    if db_exists:
        print(f"DB exists: {db_path}")
    else:
        print(f"DB initialized: {db_path}")


def stub_run_backfill(cli_options: Mapping[str, Any] | None = None): ...


def run_doctor(cli_options: Mapping[str, Any] | None = None):
    """Doctor command."""
    logger = get_logger("zotomatic.doctor", False)
    cli_options = dict(cli_options or {})
    settings = config.get_config(cli_options)

    results: list[tuple[str, str, str]] = []
    fails = 0
    warns = 0

    def _ok(section: str, message: str) -> None:
        results.append((section, "OK", message))

    def _warn(section: str, message: str) -> None:
        nonlocal warns
        warns += 1
        results.append((section, "WARN", message))

    def _fail(section: str, message: str) -> None:
        nonlocal fails
        fails += 1
        results.append((section, "FAIL", message))

    def _check_zotero_running() -> bool | None:
        if sys.platform.startswith("win"):
            try:
                result = subprocess.run(
                    ["tasklist"], capture_output=True, text=True, check=False
                )
            except OSError:
                return None
            return "Zotero.exe" in result.stdout
        try:
            result = subprocess.run(
                ["ps", "-A", "-o", "comm="],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return None
        return any("Zotero" in line for line in result.stdout.splitlines())

    config_path = settings.get("config_path")
    if config_path and Path(str(config_path)).expanduser().exists():
        _ok("Config", f"config file exists: {config_path}")
    else:
        _fail("Config", "config file not found")

    pdf_dir = settings.get("pdf_dir")
    if not pdf_dir:
        _fail("Paths", "pdf_dir is not configured (scan --path can run without it)")
    else:
        pdf_path = Path(str(pdf_dir)).expanduser()
        if not pdf_path.exists():
            _fail("Paths", f"pdf_dir does not exist: {pdf_path}")
        elif not pdf_path.is_dir():
            _fail("Paths", f"pdf_dir is not a directory: {pdf_path}")
        elif not os.access(pdf_path, os.R_OK):
            _fail("Paths", f"pdf_dir is not readable: {pdf_path}")
        else:
            _ok("Paths", f"pdf_dir is readable: {pdf_path}")

    note_dir = settings.get("note_dir")
    if not note_dir:
        _fail("Paths", "note_dir is not configured")
    else:
        note_path = Path(str(note_dir)).expanduser()
        try:
            note_path.mkdir(parents=True, exist_ok=True)
        except OSError:
            _fail("Paths", f"note_dir cannot be created: {note_path}")
        else:
            if not note_path.is_dir():
                _fail("Paths", f"note_dir is not a directory: {note_path}")
            elif not os.access(note_path, os.W_OK):
                _fail("Paths", f"note_dir is not writable: {note_path}")
            else:
                _ok("Paths", f"note_dir is writable: {note_path}")

    template_path = settings.get("template_path")
    if not template_path:
        _fail("Template", "template_path is not configured")
    else:
        template_file = Path(str(template_path)).expanduser()
        if not template_file.exists():
            _fail("Template", f"template file not found: {template_file}")
        elif not template_file.is_file():
            _fail("Template", f"template_path is not a file: {template_file}")
        else:
            _ok("Template", f"template file exists: {template_file}")

    summary_enabled = bool(settings.get("llm_summary_enabled", True))
    tag_enabled = bool(settings.get("llm_tag_enabled", True))
    if summary_enabled or tag_enabled:
        llm_section = settings.get("llm")
        provider = None
        provider_settings = None
        if isinstance(llm_section, Mapping):
            provider = str(llm_section.get("provider") or "").strip().lower()
            providers = llm_section.get("providers")
            if provider and isinstance(providers, Mapping):
                provider_settings = providers.get(provider)
        if not provider:
            _warn(
                "LLM",
                "LLM summaries/tags are enabled, but llm.provider is not set",
            )
        else:
            api_key = ""
            if isinstance(provider_settings, Mapping):
                api_key = str(provider_settings.get("api_key") or "").strip()
            if not api_key:
                _warn(
                    "LLM",
                    f"LLM provider is '{provider}', but api_key is missing; summaries/tags will be skipped",
                )
            else:
                _ok("LLM", f"LLM provider '{provider}' is configured")

    daily_limit = settings.get("llm_daily_limit")
    try:
        daily_limit_int = int(daily_limit) if daily_limit is not None else None
    except (TypeError, ValueError):
        daily_limit_int = None
    if daily_limit is not None and daily_limit_int is None:
        _warn("LLM", "llm_daily_limit is invalid; ignoring")

    zotero_running = _check_zotero_running()
    if zotero_running is True:
        _ok("Zotero", "Zotero app is running")
    elif zotero_running is False:
        _warn(
            "Zotero",
            "Zotero app is not running; notes can be generated but Zotero metadata will be unavailable",
        )
    else:
        _warn("Zotero", "Unable to determine whether Zotero app is running")

    zotero_token = str(settings.get("zotero_api_key") or "").strip()
    zotero_library_id = str(settings.get("zotero_library_id") or "").strip()
    zotero_library_scope = str(settings.get("zotero_library_scope") or "user").strip()

    if not zotero_token:
        _warn("Zotero", "zotero_api_key is not set; Zotero integration disabled")
    else:
        if not zotero_library_id:
            _warn("Zotero", "zotero_library_id is empty; defaulting to user library")
        try:
            client = zotero.Zotero(
                zotero_library_id or "0",
                zotero_library_scope or "user",
                zotero_token,
            )
            client.items(limit=1)
            _ok("Zotero", "Zotero API connection succeeded")
        except Exception as exc:  # pragma: no cover - network dependent
            _warn(
                "Zotero",
                "Zotero API connection failed; metadata enrichment disabled "
                f"({exc})",
            )

    label_map = {"OK": "✅", "WARN": "⚠️", "FAIL": "❌"}
    print("Doctor report:")
    sections = ["Config", "Paths", "Template", "LLM", "Zotero"]
    for section in sections:
        section_items = [item for item in results if item[0] == section]
        if section_items:
            status_set = {status for _, status, _ in section_items}
            if "FAIL" in status_set:
                section_icon = label_map["FAIL"]
            elif "WARN" in status_set:
                section_icon = label_map["WARN"]
            else:
                section_icon = label_map["OK"]
        else:
            section_icon = label_map["OK"]
        print("")
        print(f"* {section_icon} {section}")
        for _, status, message in section_items:
            print(f"    - {label_map.get(status, '?')} {message}")

    print(
        f"\nDoctor summary: {len(results) - warns - fails} OK, {warns} WARN, {fails} FAIL"
    )
    if fails:
        return 1
    return 0


def run_config_show(cli_options: Mapping[str, Any] | None = None):
    settings = config.get_config_with_sources(cli_options)
    keys = config.user_config_keys()
    visible_items = {k: settings.get(k, (None, "unset")) for k in keys}
    llm_entry = settings.get("llm")
    if llm_entry:
        llm_value, llm_source = llm_entry
        if isinstance(llm_value, Mapping):
            provider = llm_value.get("provider")
            if provider is not None:
                visible_items["llm.provider"] = (provider, llm_source)
            providers = llm_value.get("providers")
            if provider and isinstance(providers, Mapping):
                provider_settings = providers.get(str(provider))
                if isinstance(provider_settings, Mapping):
                    for item_key in ("api_key", "model", "base_url"):
                        if item_key in provider_settings:
                            visible_items[
                                f"llm.providers.{provider}.{item_key}"
                            ] = (provider_settings.get(item_key), llm_source)
    if not visible_items:
        print("No configurable settings available.")
        return 0
    width = max(len(key) for key in visible_items)
    rendered: dict[str, str] = {}
    for key, (value, _source) in visible_items.items():
        if key.startswith("llm.providers.") and key.endswith(".api_key") and value:
            raw = str(value)
            if len(raw) <= 8:
                masked = "***"
            else:
                masked = f"{raw[:4]}...{raw[-4:]}"
            rendered[key] = f'"{masked}"'
        else:
            rendered[key] = "" if value is None else config.render_value(value)
    value_width = max(len(value) for value in rendered.values())
    print("Effective configuration:")
    for key in sorted(visible_items):
        padded = key.ljust(width)
        value, source = visible_items[key]
        if source == "default":
            suffix = "default"
        elif source == "unset":
            suffix = "unset"
        else:
            suffix = ""
        value_str = rendered[key].ljust(value_width)
        if suffix:
            print(f"  {padded} = {value_str}  ({suffix})")
        else:
            print(f"  {padded} = {value_str}")
    return 0


def run_config_default(cli_options: Mapping[str, Any] | None = None):
    _ = cli_options
    result = config.reset_config_to_defaults()
    print(f"Config reset to defaults: {result.config_path}")
    if result.backup_path:
        print(f"Config backup created: {result.backup_path}")
    print("Warning: set pdf_dir before running scan")
    if result.template_created:
        print(f"Template created: {result.template_path}")
    else:
        print(f"Template exists: {result.template_path}")
    return 0


def run_config_migrate(cli_options: Mapping[str, Any] | None = None):
    _ = cli_options
    current_version = config.get_schema_version()
    if current_version >= config.current_schema_version():
        print("Config migration not needed")
        return 0
    result = config.migrate_config()
    normalized = config.normalize_config(result.config_path)
    if result.updated_keys or result.removed_keys:
        print(f"Config migrated: {result.config_path}")
    if result.backup_path:
        print(f"Config backup created: {result.backup_path}")
    if result.updated_keys:
        print(f"Updated keys: {', '.join(result.updated_keys)}")
    if result.removed_keys:
        unique_removed = sorted(set(result.removed_keys))
        print(f"Removed keys: {', '.join(unique_removed)}")
    if normalized.normalized and not (result.updated_keys or result.removed_keys):
        print(f"Config normalized: {normalized.config_path}")
        if normalized.backup_path:
            print(f"Config backup created: {normalized.backup_path}")
    return 0


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
        print(f"Template exists: {template_target}")
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
        print(f"Template created: {template_target}")

    if updated:
        print(f"Config updated: template_path={template_target}")
    else:
        print(f"Config exists: template_path={template_target}")


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
        logger.warning("Template not found: %s", template_target)
    if updated:
        print(f"Config updated: template_path={template_target}")
    else:
        print(f"Config exists: template_path={template_target}")


def _resolve_llm_provider(settings: Mapping[str, object]) -> str | None:
    llm_section = settings.get("llm")
    if isinstance(llm_section, Mapping):
        provider = llm_section.get("provider")
        if provider:
            return str(provider).strip().lower()
    return None


def run_llm_set(cli_options: Mapping[str, Any] | None = None):
    logger = get_logger("zotomatic.llm", False)
    cli_options = dict(cli_options or {})
    llm_provider = cli_options.get("llm_provider")
    init_result = config.initialize_config(cli_options)
    config_path = init_result.config_path

    settings = config.get_config(cli_options)
    if not llm_provider:
        llm_provider = _resolve_llm_provider(settings)
    if not llm_provider:
        logger.error("Missing required option: --provider")
        return

    provider = str(llm_provider).strip().lower()
    if provider not in LLM_PROVIDER_DEFAULTS:
        logger.error("Unsupported LLM provider: %s", provider)
        return
    defaults = LLM_PROVIDER_DEFAULTS.get(provider, {})
    api_key = cli_options.get("llm_api_key")
    model = cli_options.get("llm_model") or defaults.get("model")
    base_url = cli_options.get("llm_base_url") or defaults.get("base_url")

    updates: list[str] = []
    if config.update_config_section_value(config_path, "llm", "provider", provider):
        updates.append("llm.provider")
    if api_key is not None:
        if config.update_config_section_value(
            config_path,
            f"llm.providers.{provider}",
            "api_key",
            api_key,
        ):
            updates.append(f"llm.providers.{provider}.api_key")
    else:
        provider_settings = {}
        llm_section = settings.get("llm")
        if isinstance(llm_section, Mapping):
            providers = llm_section.get("providers")
            if isinstance(providers, Mapping):
                provider_settings = providers.get(provider, {}) or {}
        existing_key = ""
        if isinstance(provider_settings, Mapping):
            existing_key = str(provider_settings.get("api_key") or "").strip()
        if not existing_key:
            print(
                "Warning: API key not provided; set "
                f"ZOTOMATIC_LLM_{provider.upper()}_API_KEY to enable LLM calls."
            )
    if model:
        if config.update_config_section_value(
            config_path,
            f"llm.providers.{provider}",
            "model",
            model,
        ):
            updates.append(f"llm.providers.{provider}.model")
    if base_url:
        if config.update_config_section_value(
            config_path,
            f"llm.providers.{provider}",
            "base_url",
            base_url,
        ):
            updates.append(f"llm.providers.{provider}.base_url")

    if updates:
        print(f"LLM settings updated: {', '.join(updates)}")
    else:
        print("LLM settings already up to date")
    config.normalize_config(config_path)
