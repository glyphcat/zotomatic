from __future__ import annotations

import pytest

from zotomatic.errors import ZotomaticLLMConfigError
from zotomatic.llm.types import (
    LLMClientConfig,
    LLMSummaryContext,
    LLMSummaryMode,
    LLMTagsContext,
)
from zotomatic.note.types import NoteBuilderContext


def test_llm_client_config_requires_api_key() -> None:
    with pytest.raises(ZotomaticLLMConfigError):
        LLMClientConfig.from_settings({})


def test_llm_client_config_from_settings() -> None:
    config = LLMClientConfig.from_settings({
        "llm": {
            "provider": "openai",
            "providers": {
                "openai": {
                    "api_key": "key",
                    "base_url": "https://example.com",
                    "model": "model",
                }
            },
        },
        "llm_output_language": "ja",
    })
    assert config.provider == "openai"
    assert config.api_key == "key"
    assert config.base_url == "https://example.com"
    assert config.model == "model"
    assert config.language_code == "ja"


def test_llm_client_config_from_settings_gemini() -> None:
    config = LLMClientConfig.from_settings({
        "llm": {
            "provider": "gemini",
            "providers": {
                "gemini": {
                    "api_key": "gem-key",
                }
            },
        }
    })
    assert config.provider == "gemini"
    assert config.api_key == "gem-key"
    assert config.model == "gemini-2.5-flash"
    assert config.base_url == "https://generativelanguage.googleapis.com/v1beta"


def test_summary_mode_from_value() -> None:
    assert LLMSummaryMode.from_value("deep") is LLMSummaryMode.DEEP
    assert LLMSummaryMode.from_value("unknown") is LLMSummaryMode.QUICK


def test_llm_summary_context_from_builder_context() -> None:
    ctx = NoteBuilderContext(pdf_path="/tmp/test.pdf")
    summary_ctx = LLMSummaryContext.from_note_builder_context(ctx, mode="standard")
    assert summary_ctx.mode is LLMSummaryMode.STANDARD
    assert summary_ctx.pdf_path is not None


def test_llm_tags_context_from_builder_context() -> None:
    ctx = NoteBuilderContext(title="Paper", pdf_path="/tmp/test.pdf")
    tags_ctx = LLMTagsContext.from_note_builder_context(ctx)
    assert tags_ctx.paper_title == "Paper"
    assert tags_ctx.pdf_path is not None
