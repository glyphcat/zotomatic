"""Shared types for LLM integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Mapping

from zotomatic.errors import ZotomaticLLMConfigError
from zotomatic.note.types import NoteBuilderContext

ChatRole = Literal["system", "user", "assistant"]


LLM_PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "openai": {
        "model": "gpt-4o-mini",
        "base_url": "https://api.openai.com/v1",
    },
    "gemini": {
        "model": "gemini-2.5-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
    },
}


# --- Config. ---
@dataclass(frozen=True, slots=True)
class LLMClientConfig:
    provider: str
    base_url: str
    api_key: str
    model: str
    timeout: float
    language_code: str
    temperature: float = 0.0

    # TODO: base_urlを必須にするかどうか。メジャーLLMはサービス名だけ設定するのでもいいかも

    @staticmethod
    def _get_llm_section(settings: Mapping[str, object]) -> Mapping[str, object]:
        llm_section = settings.get("llm")
        if isinstance(llm_section, Mapping):
            return llm_section
        return {}

    @classmethod
    def _get_provider(cls, settings: Mapping[str, object]) -> str:
        llm_section = cls._get_llm_section(settings)
        provider = llm_section.get("provider")
        if provider:
            return str(provider).strip().lower()
        return ""

    @classmethod
    def _get_provider_settings(
        cls, settings: Mapping[str, object], provider: str
    ) -> Mapping[str, object]:
        llm_section = cls._get_llm_section(settings)
        providers = llm_section.get("providers")
        if not isinstance(providers, Mapping):
            return {}
        provider_settings = providers.get(provider)
        if isinstance(provider_settings, Mapping):
            return provider_settings
        return {}

    @classmethod
    def from_settings(cls, settings: Mapping[str, object]) -> LLMClientConfig:
        provider = cls._get_provider(settings)
        if not provider:
            raise ZotomaticLLMConfigError(
                "`llm.provider` must be configured before using the LLM client.",
                hint=(
                    f"Set `[llm] provider = \"openai\"` in "
                    f"{Path('~/.zotomatic/config.toml').expanduser()}."
                ),
            )
        if provider not in LLM_PROVIDER_DEFAULTS:
            raise ZotomaticLLMConfigError(
                f"Unsupported LLM provider: {provider}.",
                hint="Configure a supported LLM provider in llm.provider.",
            )

        provider_settings = cls._get_provider_settings(settings, provider)
        api_key = str(provider_settings.get("api_key") or "").strip()
        if not api_key:
            raise ZotomaticLLMConfigError(
                f"`llm.providers.{provider}.api_key` must be configured before using the LLM client.",
                hint=(
                    f"Set `llm.providers.{provider}.api_key` in "
                    f"{Path('~/.zotomatic/config.toml').expanduser()}."
                ),
            )

        defaults = LLM_PROVIDER_DEFAULTS.get(provider, {})
        base_url = str(
            provider_settings.get("base_url")
            or defaults.get("base_url")
            or ""
        )
        model = str(provider_settings.get("model") or defaults.get("model") or "")
        raw_timeout = settings.get("llm_timeout")
        timeout: float = raw_timeout if isinstance(raw_timeout, float) else 30.0
        language_code = str(settings.get("llm_output_language") or "en").strip() or "en"

        return cls(
            provider=provider,
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
