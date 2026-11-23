import pytest

from app.llm import (
    LLMError,
    MissingAPIKeyError,
    _parse_json_content,
    get_adapter,
)


def test_missing_key_explains_that_review_still_works(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    with pytest.raises(MissingAPIKeyError) as caught:
        get_adapter()
    message = str(caught.value)
    assert "No LLM API key is configured" in message
    assert "extraction cannot run" in message
    assert "review still work" in message


def test_both_keys_require_an_explicit_provider(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic")
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    with pytest.raises(MissingAPIKeyError, match="LLM_PROVIDER"):
        get_adapter()


def test_openai_adapter_uses_env_and_rejects_unsafe_base_urls(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    adapter = get_adapter()
    assert adapter.name == "openai"
    assert adapter.model == "gpt-4o-mini"
    assert "sk-test" not in repr(adapter)

    monkeypatch.setenv("OPENAI_BASE_URL", "http://169.254.169.254/latest")
    with pytest.raises(LLMError, match="OPENAI_BASE_URL"):
        get_adapter()


def test_json_fence_is_accepted():
    assert _parse_json_content('```json\n{"central_question": "Why?"}\n```') == {
        "central_question": "Why?"
    }
