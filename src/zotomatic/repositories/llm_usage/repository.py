from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping

from ..types import LLMUsageEntry


class LLMUsageStore(ABC):
    @abstractmethod
    def get(self, usage_date: str) -> LLMUsageEntry | None: ...

    @abstractmethod
    def upsert(self, entry: LLMUsageEntry) -> None: ...


class LLMUsageRepository(ABC):
    @property
    @abstractmethod
    def usage(self) -> LLMUsageStore: ...

    @classmethod
    def from_settings(cls, settings: Mapping[str, object]) -> "LLMUsageRepository":
        return create_llm_usage_repository(settings)


def create_llm_usage_repository(
    settings: Mapping[str, object],
) -> LLMUsageRepository:
    from .sqlite.repository import SqliteLLMUsageRepository

    return SqliteLLMUsageRepository.from_settings(settings)
