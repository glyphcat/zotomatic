from __future__ import annotations

from pathlib import Path

from zotomatic.repositories.types import (
    DirectoryState,
    LLMUsageEntry,
    LLMUsageRepositoryConfig,
    PendingEntry,
    WatcherFileState,
    WatcherStateRepositoryConfig,
    ZoteroAttachmentState,
)
from zotomatic.repositories.watcher_state.sqlite.directory_state import SqliteDirectoryStateStore
from zotomatic.repositories.watcher_state.sqlite.file_state import SqliteFileStateStore
from zotomatic.repositories.watcher_state.sqlite.meta import SqliteMetaStore
from zotomatic.repositories.watcher_state.sqlite.pending import SqlitePendingStore
from zotomatic.repositories.watcher_state.sqlite.zotero_attachment import SqliteZoteroAttachmentStore
from zotomatic.repositories.llm_usage.sqlite.usage import SqliteLLMUsageStore


def test_sqlite_meta_store(tmp_path: Path, sqlite_schema_path: Path) -> None:
    config = WatcherStateRepositoryConfig(sqlite_path=tmp_path / "state.db")
    store = SqliteMetaStore(config)
    store.set("key", "value")
    assert store.get("key") == "value"


def test_sqlite_file_state_store(tmp_path: Path, sqlite_schema_path: Path) -> None:
    config = WatcherStateRepositoryConfig(sqlite_path=tmp_path / "state.db")
    store = SqliteFileStateStore(config)
    file_path = Path("/tmp/file.pdf").resolve()
    state = WatcherFileState(file_path=file_path, mtime_ns=1, size=2, last_seen_at=3)
    store.upsert(state)
    loaded = store.get(str(file_path))
    assert loaded is not None
    assert loaded.size == 2
    assert store.count_under(file_path.parent) == 1


def test_sqlite_directory_state_store(tmp_path: Path, sqlite_schema_path: Path) -> None:
    config = WatcherStateRepositoryConfig(sqlite_path=tmp_path / "state.db")
    store = SqliteDirectoryStateStore(config)
    state = DirectoryState(dir_path=Path("/tmp"), aggregated_mtime_ns=10, last_seen_at=20)
    store.upsert(state)
    loaded = store.get("/tmp")
    assert loaded is not None
    assert loaded.aggregated_mtime_ns == 10


def test_sqlite_pending_store(tmp_path: Path, sqlite_schema_path: Path) -> None:
    config = WatcherStateRepositoryConfig(sqlite_path=tmp_path / "state.db")
    store = SqlitePendingStore(config)
    entry = PendingEntry(
        file_path=Path("/tmp/file.pdf"),
        first_seen_at=1,
        last_attempt_at=None,
        next_attempt_at=2,
        attempt_count=0,
        last_error=None,
    )
    store.upsert(entry)
    loaded = store.get("/tmp/file.pdf")
    assert loaded is not None
    assert loaded.next_attempt_at == 2
    listed = store.list_before(timestamp=3)
    assert listed
    store.delete("/tmp/file.pdf")
    assert store.get("/tmp/file.pdf") is None


def test_sqlite_zotero_attachment_store(tmp_path: Path, sqlite_schema_path: Path) -> None:
    config = WatcherStateRepositoryConfig(sqlite_path=tmp_path / "state.db")
    store = SqliteZoteroAttachmentStore(config)
    state = ZoteroAttachmentState(
        attachment_key="A",
        parent_item_key="P",
        file_path=Path("/tmp/file.pdf"),
        mtime_ns=1,
        size=2,
        sha1=None,
        last_seen_at=3,
    )
    store.upsert(state)
    loaded = store.get("A")
    assert loaded is not None
    assert loaded.parent_item_key == "P"


def test_sqlite_llm_usage_store(tmp_path: Path, sqlite_schema_path: Path) -> None:
    config = LLMUsageRepositoryConfig(sqlite_path=tmp_path / "usage.db")
    store = SqliteLLMUsageStore(config)
    entry = LLMUsageEntry(usage_date="2024-01-01", summary_count=1, tag_count=2, updated_at=3)
    store.upsert(entry)
    loaded = store.get("2024-01-01")
    assert loaded is not None
    assert loaded.tag_count == 2
