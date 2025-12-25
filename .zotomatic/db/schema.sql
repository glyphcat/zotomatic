-- Zotomatic watcher state schema (SQLite)

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO meta (key, value)
VALUES ('schema_version', '1');

CREATE TABLE IF NOT EXISTS files (
    file_path TEXT PRIMARY KEY,
    mtime_ns INTEGER NOT NULL,
    size INTEGER NOT NULL,
    sha1 TEXT,
    last_seen_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS files_last_seen_at_idx
    ON files(last_seen_at);

CREATE TABLE IF NOT EXISTS zotero_attachment (
    attachment_key TEXT PRIMARY KEY,
    parent_item_key TEXT,
    file_path TEXT,
    mtime_ns INTEGER,
    size INTEGER,
    sha1 TEXT,
    last_seen_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS zotero_attachment_last_seen_at_idx
    ON zotero_attachment(last_seen_at);

CREATE INDEX IF NOT EXISTS zotero_attachment_parent_item_idx
    ON zotero_attachment(parent_item_key);

CREATE TABLE IF NOT EXISTS pending (
    file_path TEXT PRIMARY KEY,
    first_seen_at INTEGER NOT NULL,
    last_attempt_at INTEGER,
    next_attempt_at INTEGER NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT
);

CREATE INDEX IF NOT EXISTS pending_next_attempt_idx
    ON pending(next_attempt_at);

CREATE TABLE IF NOT EXISTS directory_state (
    dir_path TEXT PRIMARY KEY,
    aggregated_mtime_ns INTEGER NOT NULL,
    last_seen_at INTEGER NOT NULL
);
