from __future__ import annotations

from typing import Mapping

from zotomatic.repositories.sqlite_base import SQLiteRepository

from ...types import LLMUsageEntry, LLMUsageRepositoryConfig
from ..repository import LLMUsageStore


class SqliteLLMUsageStore(SQLiteRepository, LLMUsageStore):
    """llm_usageテーブルへのアクセスを担当する。"""

    @classmethod
    def from_settings(cls, settings: Mapping[str, object]) -> SqliteLLMUsageStore:
        return cls(LLMUsageRepositoryConfig.from_settings(settings))

    def get(self, usage_date: str) -> LLMUsageEntry | None:
        query = """
            SELECT
                usage_date,
                summary_count,
                tag_count,
                updated_at
            FROM llm_usage
            WHERE usage_date = ?
        """
        with self._connect() as conn:
            row = conn.execute(query, (usage_date,)).fetchone()
        if row is None:
            return None
        return LLMUsageEntry(
            usage_date=row["usage_date"],
            summary_count=row["summary_count"],
            tag_count=row["tag_count"],
            updated_at=row["updated_at"],
        )

    def upsert(self, entry: LLMUsageEntry) -> None:
        query = """
            INSERT INTO llm_usage (
                usage_date,
                summary_count,
                tag_count,
                updated_at
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(usage_date) DO UPDATE SET
                summary_count=excluded.summary_count,
                tag_count=excluded.tag_count,
                updated_at=excluded.updated_at
        """
        params = (
            entry.usage_date,
            entry.summary_count,
            entry.tag_count,
            entry.updated_at,
        )
        with self._connect() as conn:
            conn.execute(query, params)
