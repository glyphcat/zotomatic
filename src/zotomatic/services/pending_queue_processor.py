from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from zotomatic.logging import get_logger
from zotomatic.services.pending_queue import PendingQueue
from zotomatic.zotero import ZoteroClient


@dataclass(frozen=True, slots=True)
class PendingQueueProcessorConfig:
    base_delay_seconds: int = 5
    max_delay_seconds: int = 60
    batch_limit: int = 50
    loop_interval_seconds: int = 3
    max_attempts: int = 10
    logger_name: str = "zotomatic.pending"

    @classmethod
    def from_settings(
        cls, settings: Mapping[str, object]
    ) -> "PendingQueueProcessorConfig":
        def _get_int(key: str, default: int) -> int:
            value = settings.get(key, default)
            if isinstance(value, bool):
                return default
            if isinstance(value, int):
                return value
            if isinstance(value, float):
                return int(value)
            if isinstance(value, str):
                try:
                    return int(value.strip())
                except ValueError:
                    return default
            return default

        return cls(
            base_delay_seconds=_get_int("pending_base_delay_seconds", 5),
            max_delay_seconds=_get_int("pending_max_delay_seconds", 60),
            batch_limit=_get_int("pending_batch_limit", 50),
            loop_interval_seconds=_get_int("pending_loop_interval_seconds", 3),
            max_attempts=_get_int("pending_max_attempts", 10),
            logger_name=str(settings.get("pending_logger_name", "zotomatic.pending")),
        )


class PendingQueueProcessor:
    """pendingキューを処理してZotero解決を試みる。"""

    def __init__(
        self,
        queue: PendingQueue,
        zotero_client: ZoteroClient,
        on_resolved: Callable[[Path], None],
        *,
        config: PendingQueueProcessorConfig | None = None,
    ) -> None:
        self._queue = queue
        self._zotero_client = zotero_client
        self._on_resolved = on_resolved
        self._config = config or PendingQueueProcessorConfig()
        self._logger = get_logger(self._config.logger_name, False)

    def run_once(self, limit: int | None = None) -> int:
        """期限になったpendingを処理し、成功件数を返す。"""

        if limit is None:
            limit = self._config.batch_limit
        processed = 0
        due_entries = self._queue.get_due(limit=limit)
        if due_entries:
            self._logger.info("Pending due entries: %s", len(due_entries))
        for entry in due_entries:
            pdf_path = Path(entry.file_path)
            if not pdf_path.exists():
                self._backoff(
                    entry.file_path,
                    entry.attempt_count,
                    "PDF not found",
                    entry.attempt_count + 1,
                )
                continue

            try:
                paper = self._zotero_client.get_paper_by_pdf(pdf_path)
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
            self._logger.info("Pending resolved: %s", entry.file_path)

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
                "Pending dropped after max attempts for %s: %s",
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
            "Pending backoff for %s (attempt=%s, next=%ss): %s",
            file_path,
            next_attempt,
            next_delay,
            error,
        )
