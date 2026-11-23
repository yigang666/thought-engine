"""Replaceable LLM adapters.

API keys are read from the environment. They are never written to disk by
this module and never included in error messages.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Protocol


class MissingAPIKeyError(RuntimeError):
    """Raised when extraction is requested and no provider key is configured."""


class LLMError(RuntimeError):
    """Raised when a provider call fails. The message is safe to show."""


class LLMAdapter(Protocol):
    name: str
    model: str

    def complete_json(self, *, system: str, user: str) -> dict:
        """Return one JSON object from the model."""


class OpenAIAdapter:
    def __init__(self, api_key: str, model: str, base_url: str):
        self.name = "openai"
        self.model = model
        self._api_key = api_key
        self._base_url = base_url

    def complete_json(self, *, system: str, user: str) -> dict:
        payload = _post_json(
            self._base_url.rstrip("/") + "/chat/completions",
            {
                "model": self.model,
                "temperature": 0.2,
                "max_tokens": 8192,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("The OpenAI response did not include a message.") from exc
        return _parse_json_content(content)


class AnthropicAdapter:
    def __init__(self, api_key: str, model: str):
        self.name = "anthropic"
        self.model = model
        self._api_key = api_key

    def complete_json(self, *, system: str, user: str) -> dict:
        payload = _post_json(
            "https://api.anthropic.com/v1/messages",
            {
                "model": self.model,
                "max_tokens": 8192,
                "temperature": 0.2,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            {
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        try:
            parts = payload["content"]
            content = "".join(
                part.get("text", "") for part in parts if isinstance(part, dict)
            )
        except (KeyError, TypeError) as exc:
            raise LLMError("The Anthropic response did not include text.") from exc
        return _parse_json_content(content)


def get_adapter() -> LLMAdapter:
    provider = os.environ.get("LLM_PROVIDER", "").strip().lower()
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()

    if provider not in ("", "openai", "anthropic"):
        raise MissingAPIKeyError(
            f"LLM_PROVIDER is {provider!r}. Use openai or anthropic. "
            "Import, parsing, and Thought Map review still work."
        )
    if provider == "" and openai_key and anthropic_key:
        raise MissingAPIKeyError(
            "Both OPENAI_API_KEY and ANTHROPIC_API_KEY are set. "
            "Set LLM_PROVIDER to openai or anthropic."
        )
    if provider == "openai" or (provider == "" and openai_key):
        if not openai_key:
            raise MissingAPIKeyError(_missing_message())
        model = os.environ.get("OPENAI_MODEL", "").strip() or "gpt-4o-mini"
        base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or "https://api.openai.com/v1"
        return OpenAIAdapter(openai_key, model, _check_base(base_url))
    if provider == "anthropic" or (provider == "" and anthropic_key):
        if not anthropic_key:
            raise MissingAPIKeyError(_missing_message())
        model = os.environ.get("ANTHROPIC_MODEL", "").strip() or "claude-3-5-haiku-latest"
        return AnthropicAdapter(anthropic_key, model)
    raise MissingAPIKeyError(_missing_message())


def _missing_message() -> str:
    return (
        "No LLM API key is configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY "
        "(optional LLM_PROVIDER=openai or anthropic). "
        "Import, parsing, and Thought Map review still work; extraction cannot run."
    )


def _check_base(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme == "https":
        return url.rstrip("/")
    if parsed.scheme == "http" and host in {"localhost", "127.0.0.1"}:
        return url.rstrip("/")
    raise LLMError(
        "OPENAI_BASE_URL must start with https://, or http://127.0.0.1 or http://localhost for a local proxy."
    )


def _post_json(url: str, body: dict, headers: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            text = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise LLMError(f"The LLM provider returned HTTP {exc.code}. {detail}") from None
    except urllib.error.URLError as exc:
        raise LLMError(f"Could not reach the LLM provider. {exc.reason}") from None
    except TimeoutError:
        raise LLMError("The LLM provider timed out.") from None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMError("The LLM provider returned non-JSON.") from exc
    if not isinstance(payload, dict):
        raise LLMError("The LLM provider returned an unexpected payload.")
    return payload


def _parse_json_content(content: str) -> dict:
    text = _strip_fence(content.strip())
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMError("The model did not return valid JSON.") from exc
    if not isinstance(payload, dict):
        raise LLMError("The model JSON was not an object.")
    return payload


def _strip_fence(text: str) -> str:
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()
