"""Configuración desde variables de entorno o un archivo .env local."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROVIDERS = {"groq", "openai", "anthropic", "ollama", "openai_compatible"}


@dataclass(frozen=True)
class Settings:
    provider: str
    model: str
    base_url: str | None
    structured_method: str | None
    strict: bool
    timeout_seconds: float
    max_retries: int
    api_key: str | None


def load_settings() -> Settings:
    # No sobreescribe variables de entorno existentes (útil en CI o servidores).
    load_dotenv(PROJECT_ROOT / ".env", override=False)

    provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()
    if provider not in PROVIDERS:
        raise ValueError(f"LLM_PROVIDER inválido: {provider}. Opciones: {', '.join(sorted(PROVIDERS))}")

    defaults = {"groq": "openai/gpt-oss-120b"}
    model = (os.getenv("LLM_MODEL") or defaults.get(provider, "")).strip()
    if not model:
        raise ValueError(f"Definí LLM_MODEL para el proveedor '{provider}' en .env")

    base_url = (os.getenv("LLM_BASE_URL") or "").strip() or None
    if provider == "openai_compatible" and not base_url:
        raise ValueError("LLM_BASE_URL es obligatorio para openai_compatible")

    method = (os.getenv("LLM_STRUCTURED_METHOD") or "").strip().lower() or None
    if method not in {None, "json_schema", "function_calling"}:
        raise ValueError("LLM_STRUCTURED_METHOD debe ser json_schema o function_calling")

    strict_value = (os.getenv("LLM_STRICT", "false") or "false").strip().lower()
    if strict_value not in {"true", "false"}:
        raise ValueError("LLM_STRICT debe ser true o false")
    strict = strict_value == "true"

    try:
        timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
        retries = int(os.getenv("LLM_MAX_RETRIES", "2"))
    except ValueError as exc:
        raise ValueError("LLM_TIMEOUT_SECONDS y LLM_MAX_RETRIES deben ser números") from exc
    if timeout <= 0 or retries < 0:
        raise ValueError("Timeout debe ser positivo y max_retries no puede ser negativo")

    env_key_by_provider = {
        "groq": "GROQ_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "openai_compatible": "LLM_API_KEY",
    }
    env_var = env_key_by_provider.get(provider)
    api_key = (os.getenv(env_var, "") if env_var else "").strip() or None
    if env_var and not api_key:
        raise ValueError(f"Falta {env_var}. Agregala a tu .env, no al código fuente.")

    return Settings(
        provider=provider,
        model=model,
        base_url=base_url,
        structured_method=method,
        strict=strict,
        timeout_seconds=timeout,
        max_retries=retries,
        api_key=api_key,
    )
