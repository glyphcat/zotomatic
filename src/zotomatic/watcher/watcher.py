from __future__ import annotations

import threading
from pathlib import Path
from typing import Iterable

from watchfiles import Change, watch

from zotomatic.errors import WatcherError
from zotomatic.logging import get_logger
from zotomatic.repositories.types import WatcherFileState
from zotomatic.watcher.types import WatcherConfig


class PDFStorageWatcher:
    """監視対象ディレクトリ内のPDFを継続的に監視するクラス。"""

    def __init__(self, config: WatcherConfig) -> None:
        self._config = config
        self._logger = get_logger(config.logger_name, config.verbose_logging)
        self._state_repository = config.state_repository
        self._seen: set[Path] = set()
        self._seen_lock = threading.Lock()
        self._retry_queue: set[Path] = set()
        self._retry_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_error: Exception | None = None

    # ----- Property -----

    @property
    def last_error(self) -> Exception | None:
        """直近のエラーを返す。"""

        return self._last_error

    @property
    def is_running(self) -> bool:
        """バックグラウンドスレッドが動作中かを返す。"""

        return self._thread is not None and self._thread.is_alive()

    # ----- External. -----
    def start(self) -> None:
        """監視を開始し、新規PDF検出時にコールバックを発火する。"""

        if self.is_running:
            self._logger.debug("Watcher already running; ignoring duplicate start().")
            return

        try:
            self._config.watch_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:  # pragma: no cover - depends on filesystem state
            raise WatcherError(
                f"Failed to prepare watch directory: {self._config.watch_dir}"
            ) from exc

        with self._seen_lock:
            self._seen.clear()
        with self._retry_lock:
            self._retry_queue.clear()

        self._stop_event.clear()
        self._last_error = None

        self._thread = threading.Thread(
            target=self._run,
            name="zotomatic-pdf-watcher",
            daemon=True,
        )
        self._thread.start()

        self._logger.info(
            "Started PDF watcher on %s (backend=watchfiles)", self._config.watch_dir
        )

    def stop(self, timeout: float | None = None) -> None:
        """監視を停止し、バックグラウンド処理を終了させる。"""

        if not self.is_running:
            return

        self._stop_event.set()
        assert self._thread is not None
        self._thread.join(timeout=timeout)
        self._thread = None

        self._logger.info("Stopped PDF watcher on %s", self._config.watch_dir)

    def simulate_pdf_saved(self, pdf_name: str) -> Path:
        """監視を介さずにコールバックを強制実行するテスト用フック"""

        pdf_path = (self._config.watch_dir / pdf_name).resolve()
        self._logger.debug("Simulating PDF save for %s", pdf_path)
        with self._seen_lock:
            self._seen.add(pdf_path)
        self._dispatch_callback(pdf_path)
        return pdf_path

    # ----- Internal. -----
    def __enter__(self) -> PDFStorageWatcher:
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()

    def _run(self) -> None:
        try:
            self._initial_scan()
            self._run_with_watchfiles()
        except Exception as exc:  # pragma: no cover - defensive guard
            self._last_error = exc
            self._logger.exception("Watcher loop aborted due to an unexpected error.")
        finally:
            self._stop_event.set()
            self._logger.debug("Watcher thread exiting.")

    def _initial_scan(self) -> None:
        self._poll_for_new_files()

    def _run_with_watchfiles(self) -> None:
        accepted_changes = {
            getattr(Change, "added", None),
            getattr(Change, "modified", None),
        }
        accepted_changes.discard(None)

        try:
            for changes in watch(
                self._config.watch_dir,
                stop_event=self._stop_event,
                recursive=True,
            ):
                if self._stop_event.is_set():
                    break
                self._retry_pending()
                for change, path_str in changes:
                    if accepted_changes and change not in accepted_changes:
                        continue
                    self._handle_candidate(Path(path_str))
        except Exception as exc:  # pragma: no cover - depends on watchfiles backend
            self._last_error = exc
            self._logger.exception(
                "watchfiles loop failed; switching to polling fallback."
            )
            if not self._stop_event.is_set():
                self._run_with_polling()

    def _poll_for_new_files(self) -> None:
        try:
            self._ensure_watch_dir()
            for pdf_path in self._scan_for_new_pdfs():
                self._handle_candidate(pdf_path)
        except WatcherError:
            raise
        except Exception as exc:  # pragma: no cover - defensive guard
            self._last_error = exc
            self._logger.exception("Polling watcher iteration failed.")

    def _ensure_watch_dir(self) -> None:
        if self._config.watch_dir.exists():
            return
        self._logger.warning(
            "Watch directory %s is missing; attempting to recreate it.",
            self._config.watch_dir,
        )
        try:
            self._config.watch_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._logger.error(
                "Failed to recreate watch directory: %s", exc, exc_info=True
            )
            raise WatcherError("Cannot recreate watch directory.") from exc

    def _scan_for_new_pdfs(self) -> Iterable[Path]:
        if not self._config.watch_dir.exists():
            return []
        try:
            return [
                p for p in sorted(self._config.watch_dir.rglob("*.pdf")) if p.is_file()
            ]
        except OSError as exc:  # pragma: no cover - depends on filesystem
            self._logger.error("Failed to list PDFs: %s", exc, exc_info=True)
            raise WatcherError("Failed to scan watch directory.") from exc

    def _handle_candidate(self, path: Path) -> None:
        try:
            resolved = path.resolve()
        except OSError:
            self._logger.debug("Could not resolve path %s; will retry later.", path)
            self._schedule_retry(path)
            return

        if resolved.suffix.lower() != self._config.pdf_suffix:
            return
        if not resolved.exists():
            self._logger.debug("Candidate %s no longer exists; skipping.", resolved)
            return
        if not self._wait_for_stable(resolved):
            self._logger.debug(
                "PDF still being written: %s; retry scheduled.", resolved
            )
            self._schedule_retry(resolved)
            return

        stat = None
        if self._state_repository:
            try:
                stat = resolved.stat()
                previous = self._state_repository.get_file_state(resolved)
                if (
                    previous
                    and previous.mtime_ns == stat.st_mtime_ns
                    and previous.size == stat.st_size
                ):
                    state = WatcherFileState.from_path(
                        file_path=resolved,
                        mtime_ns=stat.st_mtime_ns,
                        size=stat.st_size,
                    )
                    self._state_repository.upsert_file_state(state)
                    self._logger.debug(
                        "PDF unchanged since last scan; skipping: %s", resolved
                    )
                    return
            except Exception as exc:  # pragma: no cover - sqlite/filesystem dependent
                self._logger.debug(
                    "Failed to consult watcher state for %s: %s", resolved, exc
                )

        with self._seen_lock:
            if resolved in self._seen:
                self._logger.debug("PDF already processed: %s", resolved)
                return
            self._seen.add(resolved)

        if self._state_repository:
            try:
                if stat is None:
                    stat = resolved.stat()
                state = WatcherFileState.from_path(
                    file_path=resolved,
                    mtime_ns=stat.st_mtime_ns,
                    size=stat.st_size,
                )
                self._state_repository.upsert_file_state(state)
            except Exception as exc:  # pragma: no cover - sqlite/filesystem dependent
                self._logger.debug(
                    "Failed to persist watcher state for %s: %s", resolved, exc
                )

        self._logger.info("New PDF detected: %s", resolved)
        self._dispatch_callback(resolved)

    def _dispatch_callback(self, pdf_path: Path) -> None:
        try:
            self._config.on_pdf_created(pdf_path)
        except Exception as exc:  # pragma: no cover - callback定義側に依存
            self._last_error = exc
            self._logger.exception("Callback failed while handling %s", pdf_path)

    def _wait_for_stable(self, path: Path) -> bool:
        """
        保存直後のPDFは書き込みが終わっておらず破損の可能性があるためファイルサイズが複数回連続で変化しないことを確認
        """
        previous_size: int | None = None
        for _ in range(self._config.stability_checks):
            if not path.exists():
                return False
            try:
                current_size = path.stat().st_size
            except OSError:
                return False
            if previous_size is not None and current_size == previous_size:
                return True
            previous_size = current_size
            if self._stop_event.wait(self._config.stability_wait_seconds):
                break
        return False

    def _schedule_retry(self, path: Path) -> None:
        """
        _wait_for_stableチェックでファイル書き込み中だった場合は_retry_queueに追加。
        次のループで _retry_pending()により再チェックする
        """
        with self._retry_lock:
            self._retry_queue.add(path)

    def _retry_pending(self) -> None:
        with self._retry_lock:
            if not self._retry_queue:
                return
            pending = list(self._retry_queue)
            self._retry_queue.clear()

        for path in pending:
            self._handle_candidate(path)

    def _run_with_polling(self) -> None:
        while not self._stop_event.is_set():
            self._poll_for_new_files()
            if self._stop_event.wait(self._config.fallback_poll_interval):
                break
