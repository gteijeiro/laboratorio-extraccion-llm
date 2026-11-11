"""Verifica el ruteo a LangChain sin llamadas externas ni dependencias de proveedores."""

import sys
import types

import pytest
from httpx import TransportError

from extraccion_llm.config import Settings
from extraccion_llm.providers import build_structured_llm

ESQUEMA = {
    "type": "object",
    "properties": {"resumen": {"type": "string"}},
    "required": ["resumen"],
    "additionalProperties": False,
}


def config(provider: str, *, model: str = "modelo", base_url: str | None = None,
           strict: bool = False, structured_method: str | None = None) -> Settings:
    return Settings(
        provider=provider, model=model, base_url=base_url,
        strict=strict, structured_method=structured_method,
        timeout_seconds=30, max_retries=1,
        api_key=None if provider == "ollama" else "fake-key",
    )


@pytest.mark.parametrize(
    "provider,expected_backend,expected_method",
    [
        ("groq", "groq", "json_schema"),
        ("openai", "openai", "json_schema"),
        ("anthropic", "anthropic", "function_calling"),
        ("ollama", "ollama", "json_schema"),
        ("openai_compatible", "openai", "function_calling"),
    ],
)
def test_providers(monkeypatch, provider, expected_backend, expected_method):
    calls = {}

    class FakeModel:
        def with_structured_output(self, schema, **kwargs):
            calls["schema"] = schema
            calls["structured"] = kwargs
            return self

        def with_retry(self, **kwargs):
            calls["retry"] = kwargs
            return self

    def fake_init_chat_model(model_name, model_provider, **kwargs):
        calls.update(model=model_name, backend=model_provider, options=kwargs)
        return FakeModel()

    module = types.ModuleType("langchain")
    chat_models = types.ModuleType("langchain.chat_models")
    chat_models.init_chat_model = fake_init_chat_model
    module.chat_models = chat_models
    monkeypatch.setitem(sys.modules, "langchain", module)
    monkeypatch.setitem(sys.modules, "langchain.chat_models", chat_models)

    base_urls = {
        "groq": "https://api.groq.com/openai/v1/",
        "ollama": "http://localhost:11434",
        "openai_compatible": "http://localhost:9999/v1",
    }
    settings = config(provider, base_url=base_urls.get(provider))
    assert isinstance(build_structured_llm(settings, ESQUEMA), FakeModel)
    assert calls["backend"] == expected_backend
    assert calls["structured"]["method"] == expected_method
    assert calls["schema"] == {**ESQUEMA, "title": "extraccion"}
    if provider == "groq":
        assert calls["structured"]["strict"] is False
        assert calls["options"]["base_url"] == "https://api.groq.com"
    else:
        assert "strict" not in calls["structured"]
    if provider == "openai_compatible":
        assert calls["options"]["base_url"] == "http://localhost:9999/v1"
    if provider == "ollama":
        assert calls["options"] == {
            "base_url": "http://localhost:11434",
            "client_kwargs": {"timeout": 30},
        }
        assert calls["retry"] == {
            "retry_if_exception_type": (ConnectionError, TransportError),
            "stop_after_attempt": 2,
        }


def test_groq_strict_configurable(monkeypatch):
    calls = {}

    class FakeModel:
        def with_structured_output(self, schema, **kwargs):
            calls.update(kwargs)
            return self

    module = types.ModuleType("langchain")
    chat_models = types.ModuleType("langchain.chat_models")
    chat_models.init_chat_model = lambda *a, **kw: FakeModel()
    module.chat_models = chat_models
    monkeypatch.setitem(sys.modules, "langchain", module)
    monkeypatch.setitem(sys.modules, "langchain.chat_models", chat_models)

    build_structured_llm(config("groq", strict=True), ESQUEMA)
    assert calls["method"] == "json_schema"
    assert calls["strict"] is True
