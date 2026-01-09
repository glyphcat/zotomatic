from __future__ import annotations

from pathlib import Path

import pytest

from zotomatic.llm.client import BaseLLMClient
from zotomatic.llm.types import LLMClientConfig, LLMSummaryContext, LLMTagsContext


class FakeLLMClient(BaseLLMClient):
    def __init__(self, response_text: str) -> None:
        config = LLMClientConfig(
            provider="openai",
            base_url="https://example.com",
            api_key="key",
            model="model",
            timeout=5.0,
            language_code="en",
        )
        super().__init__(config)
        self.response_text = response_text
        self.calls: list[dict[str, object]] = []

    def _close(self):
        return None

    def _chat_completion(self, messages, *, temperature: float, max_tokens: int):
        self.calls.append(
            {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        return self.response_text, {"ok": True}


def test_generate_summary_missing_pdf_returns_empty(tmp_path: Path) -> None:
    client = FakeLLMClient("summary")
    context = LLMSummaryContext(pdf_path=tmp_path / "missing.pdf")
    result = client.generate_summary(context)
    assert result.summary == ""


def test_generate_summary_quick(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_text("pdf", encoding="utf-8")
    monkeypatch.setattr(
        "zotomatic.llm.client.pdf.extract_abstract_candidate",
        lambda path, logger=None: "Abstract",
    )

    client = FakeLLMClient("summary text")
    context = LLMSummaryContext(pdf_path=pdf_path)
    result = client.generate_summary(context)
    assert result.summary == "summary text"


def test_generate_tags(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_text("pdf", encoding="utf-8")
    monkeypatch.setattr(
        "zotomatic.llm.client.pdf.extract_abstract_candidate",
        lambda path, logger=None: "Abstract",
    )

    client = FakeLLMClient("tag1, tag2, tag1")
    context = LLMTagsContext(paper_title="Paper", pdf_path=pdf_path)
    result = client.generate_tags(context)
    assert result.tags == ("tag1", "tag2")
