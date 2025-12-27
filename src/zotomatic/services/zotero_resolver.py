from __future__ import annotations

import time
from pathlib import Path

from zotomatic.logging import get_logger
from zotomatic.repositories import ZoteroAttachmentState
from zotomatic.repositories.watcher_state import (
    WatcherStateRepository,
    ZoteroAttachmentStore,
)
from zotomatic.zotero import ZoteroClient
from zotomatic.zotero.types import ZoteroPaper


class ZoteroResolver:
    """Zoteroのメタデータ解決と永続化を担当する。"""

    def __init__(
        self,
        client: ZoteroClient,
        attachment_store: ZoteroAttachmentStore,
        *,
        logger_name: str = "zotomatic.zotero",
    ) -> None:
        self._client = client
        self._attachment_store = attachment_store
        self._logger = get_logger(logger_name, False)

    @classmethod
    def from_state_repository(
        cls, client: ZoteroClient, state_repository: WatcherStateRepository
    ) -> ZoteroResolver:
        return cls(client=client, attachment_store=state_repository.zotero_attachment)

    def resolve(self, pdf_path: str | Path) -> ZoteroPaper | None:
        path = Path(pdf_path)
        paper = self._client.get_paper_by_pdf(path)
        if not paper:
            return None

        mtime_ns = None
        size = None
        try:
            stat = path.stat()
            mtime_ns = stat.st_mtime_ns
            size = stat.st_size
        except OSError:
            self._logger.debug("Failed to stat PDF for resolver: %s", path)

        try:
            self._attachment_store.upsert(
                ZoteroAttachmentState(
                    attachment_key=paper.key,
                    parent_item_key=None,
                    file_path=path,
                    mtime_ns=mtime_ns,
                    size=size,
                    sha1=None,
                    last_seen_at=int(time.time()),
                )
            )
        except Exception as exc:  # pragma: no cover - sqlite dependent
            self._logger.debug("Failed to persist attachment state: %s", exc)

        return paper
