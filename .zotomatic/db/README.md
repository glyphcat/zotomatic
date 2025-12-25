# Zotomatic SQLite schema

This directory stores the SQLite schema and migrations used by Zotomatic.

- `zotomatic.db` lives next to this README but is git-ignored.
- `schema.sql` represents the latest schema snapshot.
- `migrations/` contains forward-only SQL changes.

## Tables

- `meta`
  - Stores schema metadata (e.g., `schema_version`).
- `files`
  - Tracks file states for folder-based monitoring.
  - Columns: `file_path`, `mtime_ns`, `size`, `sha1`, `last_seen_at`.
- `zotero_attachment`
  - Tracks Zotero attachments by `attachment_key`.
  - Columns: `attachment_key`, `parent_item_key`, `file_path`, `mtime_ns`, `size`, `sha1`, `last_seen_at`.
- `pending`
  - Retry queue for PDFs not yet resolved by Zotero.
  - Columns: `file_path`, `first_seen_at`, `last_attempt_at`, `next_attempt_at`, `attempt_count`, `last_error`.
- `directory_state`
  - Directory-level cache to skip unchanged paths during polling.
  - Columns: `dir_path`, `aggregated_mtime_ns`, `last_seen_at`.

## Operational flow

- On file detection, upsert into `files` with `last_seen_at`.
- If Zotero resolves an attachment, upsert into `zotero_attachment` and remove from `pending`.
- If Zotero does not resolve, insert/update `pending` with backoff fields.
- During polling fallback, use `directory_state` to skip unmodified directories.

## Indexes

Indexes (`CREATE INDEX`) speed up reads for frequent lookup patterns:

- `files_last_seen_at_idx` accelerates filtering by recency.
- `zotero_attachment_last_seen_at_idx` accelerates attachment recency checks.
- `zotero_attachment_parent_item_idx` accelerates per-item queries.
- `pending_next_attempt_idx` accelerates picking the next retry batch.
