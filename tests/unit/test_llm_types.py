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
        "llm_openai_api_key": "key",
        "llm_openai_base_url": "https://example.com",
        "llm_openai_model": "model",
        "llm_output_language": "ja",
    })
    assert config.api_key == "key"
    assert config.base_url == "https://example.com"
    assert config.model == "model"
    assert config.language_code == "ja"


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
