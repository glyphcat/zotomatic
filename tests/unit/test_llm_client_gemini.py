from __future__ import annotations

import httpx
import pytest

from zotomatic.errors import ZotomaticLLMAPIError
from zotomatic.llm.client import GeminiLLMClient
from zotomatic.llm.types import LLMClientConfig


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


class FakeHttpClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.last_url: str | None = None
        self.last_json: dict[str, object] | None = None

    def post(self, url: str, json: dict[str, object]):
        self.last_url = url
        self.last_json = json
        return FakeResponse(self.payload)

    def close(self) -> None:
        return None


def _create_config() -> LLMClientConfig:
    return LLMClientConfig(
        provider="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        api_key="key",
        model="gemini-2.5-flash",
        timeout=5.0,
        language_code="en",
    )


def test_gemini_chat_completion_builds_payload() -> None:
    payload = {
        "candidates": [
            {"content": {"parts": [{"text": "Hello"}, {"text": " world"}]}}
        ]
    }
    client = GeminiLLMClient(_create_config())
    fake_http = FakeHttpClient(payload)
    client._http_client = fake_http

    result, raw = client._chat_completion(
        [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "User prompt"},
        ],
        temperature=0.2,
        max_tokens=10,
    )

    assert result == "Hello world"
    assert raw == payload
    assert fake_http.last_url == "/models/gemini-2.5-flash:generateContent"
    assert fake_http.last_json is not None
    assert fake_http.last_json["system_instruction"] == {
        "parts": [{"text": "System prompt"}]
    }
    contents = fake_http.last_json["contents"]
    assert contents == [
        {"role": "user", "parts": [{"text": "User prompt"}]}
    ]


def test_gemini_chat_completion_raises_api_error() -> None:
    client = GeminiLLMClient(_create_config())

    request = httpx.Request("POST", "https://example.com")
    response = httpx.Response(
        400,
        request=request,
        json={
            "error": {
                "message": "Invalid argument",
                "status": "INVALID_ARGUMENT",
                "code": 400,
            }
        },
    )

    class ErrorResponse:
        def raise_for_status(self) -> None:
            raise httpx.HTTPStatusError(
                "bad request", request=request, response=response
            )

        def json(self) -> dict[str, object]:
            return response.json()

        @property
        def text(self) -> str:
            return response.text

    class ErrorHttpClient:
        def post(self, url: str, json: dict[str, object]):
            return ErrorResponse()

        def close(self) -> None:
            return None

    client._http_client = ErrorHttpClient()

    with pytest.raises(ZotomaticLLMAPIError) as excinfo:
        client._chat_completion(
            [{"role": "user", "content": "hi"}],
            temperature=0.2,
            max_tokens=10,
        )
    assert "INVALID_ARGUMENT" in str(excinfo.value)
    assert "Invalid argument" in str(excinfo.value)
