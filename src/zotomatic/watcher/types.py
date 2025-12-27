from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from zotomatic.errors import WatcherError
from zotomatic.repositories import WatcherStateRepository

_PDF_SUFFIX = ".pdf"
_STABILITY_WAIT_SECONDS = 0.5
_STABILITY_CHECKS = 4
_FALLBACK_POLL_INTERVAL = 5.0
_LOGGER_NAME = "zotomatic.watcher"


@dataclass(frozen=True, slots=True)
class WatcherConfig:
    """監視設定。設定値とウォッチャー実装の橋渡し役。"""

    watch_dir: Path
    on_pdf_created: Callable[[Path], None]
    on_initial_scan_complete: Callable[[], None] | None = None
    state_repository: WatcherStateRepository | None = None
    verbose_logging: bool = False

    def __post_init__(self) -> None:  # type: ignore[override]
        object.__setattr__(self, "watch_dir", Path(self.watch_dir).expanduser())

    @property
    def stability_wait_seconds(self) -> float:
        return _STABILITY_WAIT_SECONDS

    @property
    def stability_checks(self) -> int:
        return _STABILITY_CHECKS

    @property
    def fallback_poll_interval(self) -> float:
        return _FALLBACK_POLL_INTERVAL

    @property
    def logger_name(self) -> str:
        return _LOGGER_NAME

    @property
    def pdf_suffix(self) -> str:
        return _PDF_SUFFIX

    @classmethod
    def from_settings(
        cls,
        settings: Mapping[str, Any],
        callback: Callable[[Path], None],
        state_repository: WatcherStateRepository | None = None,
        on_initial_scan_complete: Callable[[], None] | None = None,
    ) -> WatcherConfig:
        watch_dir = settings.get("pdf_library_dir")
        if not watch_dir:
            raise WatcherError(
                "`pdf_library_dir` must be configured before starting the watcher."
            )
        verbose = bool(settings.get("watch_verbose_logging", False))
        return cls(
            watch_dir=Path(watch_dir),
            on_pdf_created=callback,
            state_repository=state_repository,
            on_initial_scan_complete=on_initial_scan_complete,
            verbose_logging=verbose,
        )
