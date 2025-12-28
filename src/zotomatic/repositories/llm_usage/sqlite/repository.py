from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ...types import LLMUsageRepositoryConfig
from ..repository import LLMUsageRepository
from .usage import SqliteLLMUsageStore


@dataclass(slots=True)
class SqliteLLMUsageRepository(LLMUsageRepository):
    """SQLite実装のLLMUsageリポジトリ集約。"""

    _usage: SqliteLLMUsageStore

    @classmethod
    def from_settings(
        cls, settings: Mapping[str, object]
    ) -> SqliteLLMUsageRepository:
        config = LLMUsageRepositoryConfig.from_settings(settings)
        return cls(_usage=SqliteLLMUsageStore(config))

    @property
    def usage(self) -> SqliteLLMUsageStore:
        return self._usage
