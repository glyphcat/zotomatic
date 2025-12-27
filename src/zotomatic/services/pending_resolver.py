from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from zotomatic.logging import get_logger
from zotomatic.services.pending_queue import PendingQueue
from zotomatic.zotero import ZoteroClient


@dataclass(frozen=True, slots=True)
class PendingResolverConfig:
    base_delay_seconds: int = 5
    max_delay_seconds: int = 60
    batch_limit: int = 50
    logger_name: str = "zotomatic.pending"

    @classmethod
    def from_settings(cls, settings: Mapping[str, object]) -> "PendingResolverConfig":
        return cls(
            base_delay_seconds=int(settings.get("pending_base_delay_seconds", 5)),
            max_delay_seconds=int(settings.get("pending_max_delay_seconds", 60)),
            batch_limit=int(settings.get("pending_batch_limit", 50)),
            logger_name=str(settings.get("pending_logger_name", "zotomatic.pending")),
        )


class PendingResolver:
    """pendingキューを処理してZotero解決を試みる。"""

    def __init__(
        self,
        queue: PendingQueue,
        zotero_client: ZoteroClient,
        on_resolved: Callable[[Path], None],
        *,
        config: PendingResolverConfig | None = None,
    ) -> None:
        self._queue = queue
        self._zotero_client = zotero_client
        self._on_resolved = on_resolved
        self._config = config or PendingResolverConfig()
        self._logger = get_logger(self._config.logger_name, False)

    def run_once(self, limit: int | None = None) -> int:
        """期限になったpendingを処理し、成功件数を返す。"""

        if limit is None:
            limit = self._config.batch_limit
        processed = 0
        for entry in self._queue.get_due(limit=limit):
            pdf_path = Path(entry.file_path)
            if not pdf_path.exists():
                self._backoff(entry.file_path, entry.attempt_count, "PDF not found")
                continue

            try:
                paper = self._zotero_client.get_paper_by_pdf(pdf_path)
            except Exception as exc:  # pragma: no cover - pyzotero runtime
                self._backoff(entry.file_path, entry.attempt_count, str(exc))
                continue

            if not paper:
                self._backoff(entry.file_path, entry.attempt_count, "Zotero unresolved")
                continue

            try:
                self._on_resolved(pdf_path)
            except Exception as exc:  # pragma: no cover - callback depends on caller
                self._backoff(entry.file_path, entry.attempt_count, str(exc))
                continue

            self._queue.resolve(entry.file_path)
            processed += 1

        return processed

    def _backoff(self, file_path: str | Path, attempt_count: int, error: str) -> None:
        next_delay = min(
            self._config.max_delay_seconds,
            self._config.base_delay_seconds * (2 ** max(attempt_count, 0)),
        )
        next_attempt_at = int(time.time()) + next_delay
        self._queue.update_attempt(
            file_path=file_path,
            attempt_count=attempt_count + 1,
            next_attempt_at=next_attempt_at,
            last_error=error,
        )
        self._logger.debug("Pending backoff for %s: %s", file_path, error)
