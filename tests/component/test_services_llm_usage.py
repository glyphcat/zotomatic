from __future__ import annotations

from dataclasses import dataclass

import pytest

from zotomatic.errors import ZotomaticLLMUsageError
from zotomatic.repositories.types import LLMUsageEntry
from zotomatic.services.llm_usage import LLMUsageService


@dataclass
class MemoryUsageStore:
    data: dict[str, LLMUsageEntry]

    def get(self, usage_date: str):
        return self.data.get(usage_date)

    def upsert(self, entry: LLMUsageEntry) -> None:
        self.data[entry.usage_date] = entry


@dataclass
class MemoryUsageRepository:
    usage: MemoryUsageStore


def test_llm_usage_service_records() -> None:
    store = MemoryUsageStore(data={})
    repo = MemoryUsageRepository(usage=store)
    service = LLMUsageService(repository=repo, daily_limit=2, logger=None)

    assert service.can_run("summary") is True
    service.record_success("summary")
    service.record_success("tag")
    assert service.get_total_used() == 2
    assert service.can_run("summary") is False


def test_llm_usage_service_invalid_kind() -> None:
    store = MemoryUsageStore(data={})
    repo = MemoryUsageRepository(usage=store)
    service = LLMUsageService(repository=repo, daily_limit=None, logger=None)
    with pytest.raises(ZotomaticLLMUsageError):
        service.record_success("other")
