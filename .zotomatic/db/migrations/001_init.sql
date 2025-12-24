-- 001_init.sql

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO meta (key, value)
VALUES ('schema_version', '1');

CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    mtime_ns INTEGER NOT NULL,
    size INTEGER NOT NULL,
    sha1 TEXT,
    last_seen_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS files_last_seen_at_idx
    ON files(last_seen_at);
