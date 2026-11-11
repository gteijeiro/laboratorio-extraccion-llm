"""Inicialización de LangChain con proveedores intercambiables."""

from typing import Any

from .config import Settings


def build_structured_llm(settings: Settings, esquema: dict[str, Any]):
    # Importación diferida: permite usar modelos y tests sin iniciar ninguna API.
    provider = "openai" if settings.provider == "openai_compatible" else settings.provider
    if provider == "ollama":
        kwargs = {"client_kwargs": {"timeout": settings.timeout_seconds}}
    else:
        kwargs = {
            "max_retries": settings.max_retries,
            "timeout": settings.timeout_seconds,
        }
    if settings.base_url:
        base_url = settings.base_url
        if provider == "groq":
            # El SDK de Groq agrega /openai/v1 a la URL base.
            base_url = base_url.rstrip("/").removesuffix("/openai/v1")
        kwargs["base_url"] = base_url
    if settings.api_key:
        kwargs["api_key"] = settings.api_key

    # Anthropic usa su propia API y puede tener métodos distintos a Groq/OpenAI.
    default_methods = {
        "groq": "json_schema",
        "openai": "json_schema",
        "ollama": "json_schema",
        "anthropic": "function_calling",
        "openai_compatible": "function_calling",
    }
    method = settings.structured_method or default_methods[settings.provider]
    kwargs_structured = {"method": method}
    if settings.provider == "groq" and method == "json_schema":
        kwargs_structured["strict"] = settings.strict

    try:
        from langchain.chat_models import init_chat_model

        llm = init_chat_model(settings.model, model_provider=provider, **kwargs)
        esquema_proveedor = {**esquema, "title": "extraccion"}
        structured_llm = llm.with_structured_output(esquema_proveedor, **kwargs_structured)
        if provider == "ollama" and settings.max_retries:
            from httpx import TransportError

            structured_llm = structured_llm.with_retry(
                retry_if_exception_type=(ConnectionError, TransportError),
                stop_after_attempt=settings.max_retries + 1,
            )
        return structured_llm
    except ImportError:
        raise RuntimeError(
            f"Falta la integración de LangChain para {settings.provider}. "
            "Revisá los extras de instalación del README."
        ) from None
    except Exception:
        raise RuntimeError(
            "No se pudo configurar el proveedor. "
            "Revisá LLM_MODEL, LLM_BASE_URL y LLM_STRUCTURED_METHOD."
        ) from None
