from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date
from typing import Any

from zotomatic.repositories import LLMUsageEntry, LLMUsageRepository


@dataclass(slots=True)
class LLMUsageService:
    """日次のLLM使用回数を管理する。"""

    repository: LLMUsageRepository
    daily_limit: int | None
    logger: Any

    def __post_init__(self) -> None:
        self.daily_limit = self._coerce_limit(self.daily_limit)

    def can_run(self, kind: str) -> bool:
        if self.daily_limit is None or self.daily_limit <= 0:
            return True
        used = self.get_total_used()
        return used < self.daily_limit

    def get_total_used(self) -> int:
        entry = self._get_entry()
        return entry.summary_count + entry.tag_count

    def record_success(self, kind: str) -> None:
        entry = self._get_entry(create=True)
        if kind == "summary":
            summary_count = entry.summary_count + 1
            tag_count = entry.tag_count
        elif kind == "tag":
            summary_count = entry.summary_count
            tag_count = entry.tag_count + 1
        else:
            raise ValueError(f"Unknown LLM usage kind: {kind}")
        updated = LLMUsageEntry(
            usage_date=entry.usage_date,
            summary_count=summary_count,
            tag_count=tag_count,
            updated_at=int(time.time()),
        )
        self.repository.usage.upsert(updated)

    def _get_entry(self, create: bool = False) -> LLMUsageEntry:
        usage_date = date.today().isoformat()
        entry = self.repository.usage.get(usage_date)
        if entry is not None:
            return entry
        if not create:
            return LLMUsageEntry(
                usage_date=usage_date,
                summary_count=0,
                tag_count=0,
                updated_at=int(time.time()),
            )
        entry = LLMUsageEntry(
            usage_date=usage_date,
            summary_count=0,
            tag_count=0,
            updated_at=int(time.time()),
        )
        self.repository.usage.upsert(entry)
        return entry

    def _coerce_limit(self, value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(value.strip())
            except ValueError:
                return None
        return None
