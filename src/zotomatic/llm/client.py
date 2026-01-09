"""LLM client abstractions and OpenAI implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Mapping

import httpx

from zotomatic import i18n
from zotomatic.errors import ZotomaticLLMAPIError, ZotomaticLLMClientError
from zotomatic.llm import prompts
from zotomatic.logging import get_logger
from zotomatic.utils import pdf

from .types import (
    LLMClientConfig,
    LLMSummaryContext,
    LLMSummaryMode,
    LLMSummaryResult,
    LLMTagResult,
    LLMTagsContext,
)


# --- LLM client base. ---
class BaseLLMClient(ABC):
    # チャンキング設定(定数)
    _DEEP_CHUNK_SENTENCE_RANGE = (3, 5)
    _DEEP_REDUCE_SENTENCE_RANGE = (6, 8)
    _SUMMARY_QUICK_MAX_TOKENS = 600
    _SUMMARY_STANDARD_MAX_TOKENS = 900
    _SUMMARY_DEEP_CHUNK_MAX_TOKENS = 400
    _SUMMARY_DEEP_REDUCE_MAX_TOKENS = 900
    _TAGS_MAX_TOKENS = 400

    def __init__(self, config: LLMClientConfig):
        self._config = config
        self._logger = get_logger("zotomatic.llm", False)

    @abstractmethod
    def _close(self):
        """Close client."""
        raise NotImplementedError

    @abstractmethod
    def _chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, dict[str, Any]]:
        """Call LLM chat completion"""
        raise NotImplementedError

    def _format_prompt_messages(
        self,
        template: Mapping[str, str],
        **variables: Any,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if (system_prompt := template.get("system")) is not None:
            messages.append(
                {"role": "system", "content": system_prompt.format(**variables)}
            )
        if (user_prompt := template.get("user")) is not None:
            messages.append(
                {"role": "user", "content": user_prompt.format(**variables)}
            )
        return messages

    def _summarize_quick(
        self,
        language: str,
        abstract: str,
    ) -> tuple[str, dict[str, Any]]:
        template = prompts.get_prompt("summary_quick")
        messages = self._format_prompt_messages(
            template,
            language=language,
            abstract=abstract,
        )
        summary, response = self._chat_completion(
            messages,
            temperature=self._config.temperature,
            max_tokens=self._SUMMARY_QUICK_MAX_TOKENS,
        )
        return summary, response

    def _summarize_standard(
        self,
        language: str,
        abstract: str,
        pdf_path: Path,
    ) -> tuple[str, dict[str, Any]]:
        # TODO: Utilsなどへの移動
        def _render_section_samples(snippets: Any) -> str:
            lines: list[str] = []
            for snippet in snippets or []:
                title = getattr(snippet, "title", "").strip()
                preview = getattr(snippet, "preview", "").strip()
                if not title:
                    continue
                if preview:
                    lines.append(f"{title}\n{preview}")
                else:
                    lines.append(title)
            return "\n\n".join(lines) or "No additional section excerpts were detected."

        template = prompts.get_prompt("summary_standard")
        try:
            snippets = pdf.extract_section_snippets(pdf_path)
        except Exception as exc:  # pragma: no cover - fitz edge cases
            self._logger.debug("Failed to extract section snippets: %s", exc)
            snippets = []
        section_samples = _render_section_samples(snippets)
        messages = self._format_prompt_messages(
            template,
            language=language,
            abstract=abstract,
            section_samples=section_samples,
        )
        summary, response = self._chat_completion(
            messages,
            temperature=self._config.temperature,
            max_tokens=self._SUMMARY_STANDARD_MAX_TOKENS,
        )
        return summary, {"mode": "standard", "response": response}

    def _summarize_deep(
        self,
        language: str,
        abstract: str,
        pdf_path: Path,
    ) -> tuple[str, dict[str, Any]]:
        """deep mode"""
        chunk_texts = [
            chunk.strip() for chunk in pdf.iter_chunks(pdf_path) if chunk.strip()
        ]
        if not chunk_texts:
            self._logger.debug(
                "Deep mode fallback: no chunks detected, using standard summary"
            )
            return self._summarize_standard(language, abstract, pdf_path)

        chunk_template = prompts.get_prompt("summary_deep_chunk")
        chunk_min, chunk_max = self._DEEP_CHUNK_SENTENCE_RANGE
        chunk_responses: list[dict[str, Any]] = []
        chunk_summaries: list[str] = []
        chunk_count = len(chunk_texts)
        for index, chunk_text in enumerate(chunk_texts, start=1):
            messages = self._format_prompt_messages(
                chunk_template,
                language=language,
                chunk_index=index,
                chunk_count=chunk_count,
                sentences_min=chunk_min,
                sentences_max=chunk_max,
                chunk_text=chunk_text,
            )
            summary, response = self._chat_completion(
                messages,
                temperature=self._config.temperature,
                max_tokens=self._SUMMARY_DEEP_CHUNK_MAX_TOKENS,
            )
            chunk_summaries.append(summary)
            chunk_responses.append(response)

        reduce_prompt = prompts.get_prompt("summary_deep_reduce")
        reduce_min, reduce_max = self._DEEP_REDUCE_SENTENCE_RANGE
        abstract_text = abstract.strip() or "No abstract text was detected in the PDF."
        chunk_summary_text = (
            "\n\n".join(
                (
                    f"[Chunk {idx}] {text.strip()}"
                    if text.strip()
                    else f"[Chunk {idx}] (no summary)"
                )
                for idx, text in enumerate(chunk_summaries, start=1)
            )
            or "(no chunk summaries)"
        )
        messages = self._format_prompt_messages(
            reduce_prompt,
            language=language,
            sentences_min=reduce_min,
            sentences_max=reduce_max,
            abstract=abstract_text,
            chunk_summaries=chunk_summary_text,
        )
        summary, reduce_response = self._chat_completion(
            messages,
            temperature=self._config.temperature,
            max_tokens=self._SUMMARY_DEEP_REDUCE_MAX_TOKENS,
        )

        return summary, {
            "mode": "deep",
            "chunk_responses": chunk_responses,
            "reduce_response": reduce_response,
        }

    def generate_summary(
        self,
        context: LLMSummaryContext,
    ) -> LLMSummaryResult:
        """Generate summary."""
        if not isinstance(context, LLMSummaryContext):
            raise ZotomaticLLMClientError("LLMSummaryContext instance is required")

        self._logger.debug(
            "Generating summary via %s (mode=%s, citekey=%s)",
            type(self).__name__,
            context.mode,
            None,
        )
        mode: LLMSummaryMode = LLMSummaryMode.from_value(context.mode)
        pdf_path = context.pdf_path
        if not pdf_path:
            self._logger.warning("No PDF path provided; skipping summary generation.")
            return LLMSummaryResult(mode)

        resolved_pdf = Path(pdf_path)
        if not resolved_pdf.exists():
            self._logger.warning("PDF path does not exist: %s", resolved_pdf)
            return LLMSummaryResult(mode)

        language = i18n.get_language_display(self._config.language_code)
        abstract = pdf.extract_abstract_candidate(
            path=resolved_pdf, logger=self._logger
        )
        try:
            params = {
                "language": language,
                "abstract": abstract,
                "pdf_path": resolved_pdf,
            }
            if mode is LLMSummaryMode.QUICK:
                params.pop("pdf_path")
            summary_mode_handlers = {
                LLMSummaryMode.QUICK: self._summarize_quick,
                LLMSummaryMode.STANDARD: self._summarize_standard,
                LLMSummaryMode.DEEP: self._summarize_deep,
            }
            summary, raw_response = summary_mode_handlers[mode](**params)
        except NotImplementedError:
            self._logger.debug(
                "%s does not implement summary generation", type(self).__name__
            )
            return LLMSummaryResult(mode)
        except Exception:  # pragma: no cover
            self._logger.exception("Summary generation failed")
            return LLMSummaryResult(mode)
        return LLMSummaryResult(mode, summary, raw_response)

    def generate_tags(
        self,
        context: LLMTagsContext,
    ) -> LLMTagResult:
        """Generate tags."""
        if not isinstance(context, LLMTagsContext):
            raise ZotomaticLLMClientError("LLMTagsContext instance is required")

        self._logger.debug(
            "Generating tags via %s (citekey=%s)",
            type(self).__name__,
            None,
        )

        pdf_path = context.pdf_path
        if not pdf_path:
            self._logger.warning("No PDF path provided; skipping tag generation.")
            return LLMTagResult()
        resolved_pdf = Path(pdf_path)
        if not resolved_pdf.exists():
            self._logger.warning("PDF path does not exist: %s", resolved_pdf)
            return LLMTagResult()

        language = i18n.get_language_display(self._config.language_code)
        abstract = pdf.extract_abstract_candidate(
            path=resolved_pdf, logger=self._logger
        )

        template = prompts.get_prompt("tags")
        messages = self._format_prompt_messages(
            template,
            language=language,
            abstract=abstract,
            title=context.paper_title,
            tags_max=8,
        )
        result, raw_response = self._chat_completion(
            messages,
            temperature=self._config.temperature,
            max_tokens=self._TAGS_MAX_TOKENS,
        )
        tags: list[str] = []
        if result:
            for item in result.split(","):
                tag = item.strip()
                if not tag:
                    continue
                if tag not in tags:
                    tags.append(tag)

        return LLMTagResult(tags=tuple(tags), raw_response=raw_response)

    def close(self):
        """Close LLM client."""
        self._close()


# --- LLM clients.---
class OpenAILLMClient(BaseLLMClient):
    """OpenAI ChatGPT-backed implementation for summaries and tags."""

    def __init__(self, config: LLMClientConfig):
        super().__init__(config)
        base_url = (config.base_url or "https://api.openai.com/v1").rstrip("/")
        self._http_client = httpx.Client(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            timeout=config.timeout,
        )

    def _close(self):
        """Implementation of BaseLLMClient._close()"""
        try:
            self._http_client.close()
            # TODO: エラー処理
        except NotImplementedError:
            self._logger.debug("%s does not implement _close", type(self).__name__)
        except:
            # TODO: Internal error.
            self._logger.debug("Internal errors occurred at %s", type(self).__name__)

    def _chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, dict[str, Any]]:
        """
        Implementation of BaseLLMClient._chat_completion()

        Send a completion request and return a response.
        """
        payload = {
            "model": self._config.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        response = self._http_client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        content: str = ""
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):  # pragma: no cover - defensive
            self._logger.debug("OpenAI response missing content field")
        return content.strip(), data


class GeminiLLMClient(BaseLLMClient):
    """Google Gemini-backed implementation for summaries and tags."""

    # NOTE:
    # Gemini 2.5 counts hidden "thoughts" tokens against maxOutputTokens,
    # so we raise defaults to avoid truncated outputs.
    _SUMMARY_QUICK_MAX_TOKENS = 1200
    _SUMMARY_STANDARD_MAX_TOKENS = 2000
    _SUMMARY_DEEP_CHUNK_MAX_TOKENS = 1200
    _SUMMARY_DEEP_REDUCE_MAX_TOKENS = 2200
    _TAGS_MAX_TOKENS = 800

    def __init__(self, config: LLMClientConfig):
        super().__init__(config)
        base_url = (
            config.base_url or "https://generativelanguage.googleapis.com/v1beta"
        ).rstrip("/")
        self._http_client = httpx.Client(
            base_url=base_url,
            headers={
                "x-goog-api-key": config.api_key,
                "Content-Type": "application/json",
            },
            timeout=config.timeout,
        )

    def _close(self):
        """Implementation of BaseLLMClient._close()"""
        try:
            self._http_client.close()
        except NotImplementedError:
            self._logger.debug("%s does not implement _close", type(self).__name__)
        except:
            self._logger.debug("Internal errors occurred at %s", type(self).__name__)

    def _chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, dict[str, Any]]:
        system_texts: list[str] = []
        contents: list[dict[str, Any]] = []
        for message in messages:
            role = message.get("role")
            content = message.get("content", "")
            if role == "system":
                if content.strip():
                    system_texts.append(content)
                continue
            gemini_role = "model" if role == "assistant" else "user"
            contents.append(
                {
                    "role": gemini_role,
                    "parts": [{"text": content}],
                }
            )

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_texts:
            payload["system_instruction"] = {
                "parts": [{"text": "\n".join(system_texts)}]
            }

        # NOTE: REST API
        # https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent
        response = self._http_client.post(
            f"/models/{self._config.model}:generateContent",
            json=payload,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            message = f"Gemini API error ({status_code})"
            try:
                data = exc.response.json()
            except ValueError:
                data = None
            if isinstance(data, dict):
                error = data.get("error")
                if isinstance(error, dict):
                    detail = str(error.get("message") or "").strip()
                    status = str(error.get("status") or "").strip()
                    code = error.get("code")
                    code_text = str(code).strip() if code is not None else ""
                    parts = [item for item in (code_text, status) if item]
                    label = " ".join(parts)
                    if detail:
                        if label:
                            message = f"Gemini API error ({label}): {detail}"
                        else:
                            message = f"Gemini API error: {detail}"
                    elif label:
                        message = f"Gemini API error ({label})"
            elif exc.response.text:
                message = f"Gemini API error ({status_code}): {exc.response.text}"
            raise ZotomaticLLMAPIError(message) from exc
        data = response.json()
        content: str = ""
        try:
            parts = data["candidates"][0]["content"]["parts"]
            if isinstance(parts, list):
                content = "".join(
                    part.get("text", "") for part in parts if isinstance(part, dict)
                )
        except (KeyError, IndexError, TypeError):  # pragma: no cover - defensive
            self._logger.debug("Gemini response missing content field")
        return content.strip(), data


# TODO: ここの処理はzoteroClient, NoteBuilder同様にpipelineでやるべきかも
def create_llm_client(settings: Mapping[str, object]) -> BaseLLMClient:
    # TODO: インスタンス生成処理拡張. settingsからモデルに応じたインスタンスを返却するよう修正
    config = LLMClientConfig.from_settings(settings)
    if config.provider == "openai":
        return OpenAILLMClient(config)
    if config.provider == "gemini":
        return GeminiLLMClient(config)
    raise ZotomaticLLMClientError(f"Unsupported LLM provider: {config.provider}")
