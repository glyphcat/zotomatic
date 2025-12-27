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
        cls, settings: Mapping[str, object]
    ) -> "PendingQueueProcessorConfig":
        def _get_int(key: str, default: int) -> int:
            value = settings.get(key, default)
            if isinstance(value, bool):
                return default
            if isinstance(value, int):
                return value
            if isinstance(value, float):
                return int(value)
            if isinstance(value, str):
                try:
                    return int(value.strip())
                except ValueError:
                    return default
            return default

        return cls(
            base_delay_seconds=_get_int("pending_base_delay_seconds", 5),
            max_delay_seconds=_get_int("pending_max_delay_seconds", 60),
            batch_limit=_get_int("pending_batch_limit", 50),
            loop_interval_seconds=_get_int("pending_loop_interval_seconds", 3),
            max_attempts=_get_int("pending_max_attempts", 10),
            logger_name=str(settings.get("pending_logger_name", "zotomatic.pending")),
        )
