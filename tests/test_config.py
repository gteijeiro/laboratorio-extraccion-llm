import os

import pytest
from dotenv import dotenv_values

from extraccion_llm import config


@pytest.fixture(autouse=True)
def entorno_de_prueba(monkeypatch, tmp_path):
    plantilla = config.PROJECT_ROOT / ".env.example"
    variables = dotenv_values(plantilla, interpolate=False)
    entorno = {key: value for key, value in os.environ.items() if key not in variables}
    monkeypatch.setattr(os, "environ", entorno)
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)
    (tmp_path / ".env").write_bytes(plantilla.read_bytes())


def test_config_groq(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-testing-only")
    settings = config.load_settings()
    assert settings.provider == "groq"
    assert settings.model == "openai/gpt-oss-120b"
    assert settings.api_key == "fake-key-testing-only"


def test_falla_si_falta_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("LLM_MODEL", "openai/gpt-oss-120b")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        config.load_settings()


def test_url_obligatoria_para_endpoint_compatible(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_MODEL", "mi-modelo")
    monkeypatch.setenv("LLM_API_KEY", "fake-key-testing-only")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    with pytest.raises(ValueError, match="LLM_BASE_URL"):
        config.load_settings()
