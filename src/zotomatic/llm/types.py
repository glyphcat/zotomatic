"""Shared types for LLM integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Mapping

from zotomatic.note.types import NoteBuilderContext

ChatRole = Literal["system", "user", "assistant"]


# --- Config. ---
@dataclass(frozen=True, slots=True)
class LLMClientConfig:
    base_url: str
    api_key: str
    model: str
    timeout: float
    language_code: str
    temperature: float = 0.0

    # TODO: base_urlを必須にするかどうか。メジャーLLMはサービス名だけ設定するのでもいいかも

    @classmethod
    def from_settings(cls, settings: Mapping[str, object]) -> LLMClientConfig:
        api_key = str(settings.get("llm_api_key") or "").strip()
        if not api_key:
            raise ValueError(
                "`llm_api_key` must be configured before using the LLM client."
            )

        base_url = str(settings.get("llm_base_url") or "https://api.openai.com/v1")
        model = str(settings.get("llm_model") or "gpt-4o-mini")
        raw_timeout = settings.get("llm_timeout")
        timeout: float = raw_timeout if isinstance(raw_timeout, float) else 30.0
        language_code = str(settings.get("llm_output_language") or "en").strip() or "en"

        return cls(
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout=timeout,
            language_code=language_code,
        )


# --- Context. ---
class LLMSummaryMode(str, Enum):
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"

    @classmethod
    def from_value(cls, value: str | None) -> LLMSummaryMode:
        if value is None:
            return cls.QUICK
        normalized = value.strip().lower()
        for item in cls:
            if item.value == normalized:
                return item
        return cls.QUICK


@dataclass(frozen=True, slots=True)
class LLMSummaryContext:
    """Minimal context required for LLM-based summarization."""

    mode: LLMSummaryMode = LLMSummaryMode.QUICK
    pdf_path: Path | None = None

    @classmethod
    def from_note_builder_context(
        cls, note_context: NoteBuilderContext, mode: str = "quick"
    ) -> LLMSummaryContext:
        pdf = Path(note_context.pdf_path) if note_context.pdf_path else None
        return cls(mode=LLMSummaryMode.from_value(mode), pdf_path=pdf)


@dataclass(frozen=True, slots=True)
class LLMTagsContext:
    """Minimal context required for LLM-based tag generation."""

    paper_title: str
    pdf_path: Path | None = None

    @classmethod
    def from_note_builder_context(
        cls, note_context: NoteBuilderContext
    ) -> LLMTagsContext:
        pdf = Path(note_context.pdf_path) if note_context.pdf_path else None
        existing = tuple(note_context.generated_tags)
        return cls(paper_title=note_context.title, pdf_path=pdf)


# --- Result classes. ---
@dataclass(frozen=True, slots=True)
class LLMSummaryResult:
    mode: LLMSummaryMode
    summary: str = ""
    raw_response: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class LLMTagResult:
    tags: tuple[str, ...] = ()
    raw_response: dict[str, Any] | None = None
