from __future__ import annotations

import threading
import time
from collections.abc import Callable
from pathlib import Path

import fitz

from zotomatic.logging import get_logger
from zotomatic.services.pending_queue import PendingQueue
from zotomatic.services.types import PendingQueueProcessorConfig
from zotomatic.services.zotero_resolver import ZoteroResolver


class PendingQueueProcessor:
    """pendingキューを処理してZotero解決を試みる。"""

    def __init__(
        self,
        queue: PendingQueue,
        zotero_resolver: ZoteroResolver,
        on_resolved: Callable[[Path], None],
        *,
        config: PendingQueueProcessorConfig | None = None,
        stop_event: threading.Event | None = None,
    ) -> None:
        self._queue = queue
        self._zotero_resolver = zotero_resolver
        self._on_resolved = on_resolved
        self._config = config or PendingQueueProcessorConfig()
        self._logger = get_logger(self._config.logger_name, False)
        self._stop_event = stop_event

    def run_once(self, limit: int | None = None) -> int:
        """期限になったpendingを処理し、成功件数を返す。"""

        if limit is None:
            limit = self._config.batch_limit
        processed = 0
        due_entries = self._queue.get_due(limit=limit)
        if due_entries:
            self._logger.info("Pending entries due: %s", len(due_entries))
        if due_entries and not self._zotero_resolver.is_enabled:
            for entry in due_entries:
                self._drop_permanent(
                    entry.file_path,
                    "Zotero settings missing (library_id/api_key)",
                )
            return 0
        for entry in due_entries:
            if self._stop_event and self._stop_event.is_set():
                break
            pdf_path = Path(entry.file_path)
            if not pdf_path.exists():
                self._drop_permanent(entry.file_path, "PDF not found")
                continue
            if not self._is_pdf_readable(pdf_path):
                self._drop_permanent(entry.file_path, "PDF is unreadable")
                continue

            try:
                paper = self._zotero_resolver.resolve(pdf_path)
            except Exception as exc:  # pragma: no cover - pyzotero runtime
                self._backoff(
                    entry.file_path,
                    entry.attempt_count,
                    str(exc),
                    entry.attempt_count + 1,
                )
                continue

            if not paper:
                self._backoff(
                    entry.file_path,
                    entry.attempt_count,
                    "Zotero unresolved",
                    entry.attempt_count + 1,
                )
                continue

            try:
                self._on_resolved(pdf_path)
            except Exception as exc:  # pragma: no cover - callback depends on caller
                self._backoff(
                    entry.file_path,
                    entry.attempt_count,
                    str(exc),
                    entry.attempt_count + 1,
                )
                continue

            self._queue.resolve(entry.file_path)
            processed += 1
            self._logger.info("Pending entry resolved: %s", entry.file_path)

        return processed

    @property
    def loop_interval_seconds(self) -> int:
        return self._config.loop_interval_seconds

    def _backoff(
        self, file_path: str | Path, attempt_count: int, error: str, next_attempt: int
    ) -> None:
        if next_attempt > self._config.max_attempts:
            self._queue.resolve(file_path)
            self._logger.warning(
                "Pending entry dropped after max attempts: %s (%s)",
                file_path,
                error,
            )
            return
        next_delay = min(
            self._config.max_delay_seconds,
            self._config.base_delay_seconds * (2 ** max(attempt_count, 0)),
        )
        next_attempt_at = int(time.time()) + next_delay
        self._queue.update_attempt(
            file_path=file_path,
            attempt_count=next_attempt,
            next_attempt_at=next_attempt_at,
            last_error=error,
        )
        self._logger.info(
            "Pending entry backoff: %s (attempt=%s, next=%ss): %s",
            file_path,
            next_attempt,
            next_delay,
            error,
        )

    def _drop_permanent(self, file_path: str | Path, reason: str) -> None:
        self._queue.resolve(file_path)
        self._logger.warning("Pending entry dropped: %s (%s)", file_path, reason)

    def _is_pdf_readable(self, pdf_path: Path) -> bool:
        """PDFファイル破損チェック"""
        try:
            doc = fitz.open(pdf_path)
        except Exception:
            return False
        else:
            doc.close()
            return True

    @property
    def stop_event(self) -> threading.Event | None:
        return self._stop_event
