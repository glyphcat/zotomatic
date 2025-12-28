from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PendingQueueProcessorConfig:
    base_delay_seconds: int = 5
    max_delay_seconds: int = 60
    batch_limit: int = 50
    loop_interval_seconds: int = 3
    max_attempts: int = 10
    logger_name: str = "zotomatic.pending"

    @classmethod
    def from_settings(
        cls, _settings: Mapping[str, object]
    ) -> "PendingQueueProcessorConfig":
        return cls()
