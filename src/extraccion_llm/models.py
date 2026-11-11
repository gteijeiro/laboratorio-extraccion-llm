"""Datos de entrada y casos de ejemplo independientes del tema."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator


class Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    texto: str
    contexto: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("texto")
    @classmethod
    def validar_texto(cls, texto: str) -> str:
        if not texto.strip():
            raise ValueError("El texto debe contener al menos un carácter visible")
        return texto


class Ejemplo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1)
    entrada: Entrada
    salida_esperada: dict[str, JsonValue] | None = None
    fecha_referencia: date | None = None
