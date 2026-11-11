"""Carga las instrucciones, el esquema y los casos de un tema en Markdown."""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError
from pydantic import TypeAdapter
from pydantic import ValidationError as ErrorPydantic
from referencing import Registry
from referencing.exceptions import Unresolvable

from .diseno_markdown import leer_ejemplos, leer_modelo
from .models import Ejemplo, Entrada

SECCIONES = re.compile(
    r"^## (Output Model Design|Input Model Design|Examples|Instrucciones|Esquema|Ejemplos)[ \t]*$",
    re.MULTILINE,
)
BLOQUE_JSON = re.compile(r"^```json[ \t]*\n(.*?)\n```[ \t]*$", re.DOTALL)


def _crear_validador(esquema: dict[str, Any]) -> Draft202012Validator:
    # El registro vacío impide resolver referencias mediante la red.
    return Draft202012Validator(
        esquema, format_checker=Draft202012Validator.FORMAT_CHECKER, registry=Registry()
    )


@dataclass(frozen=True)
class Tema:
    instrucciones: str
    esquema: dict[str, Any]
    ejemplos: tuple[Ejemplo, ...] = ()
    esquema_entrada: dict[str, Any] | None = None
    campo_texto: str = "texto"
    _validador: Draft202012Validator = field(init=False, repr=False)
    _validador_entrada: Draft202012Validator | None = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        if not self.instrucciones.strip():
            raise ValueError("El tema debe incluir instrucciones")
        if not isinstance(self.esquema, dict) or (
            self.esquema.get("type") != "object"
            or not isinstance(self.esquema.get("properties"), dict)
        ):
            raise ValueError("El esquema debe definir un objeto con properties")
        try:
            Draft202012Validator.check_schema(self.esquema)
        except SchemaError:
            raise ValueError("La sección Esquema no contiene un JSON Schema válido") from None

        object.__setattr__(self, "_validador", _crear_validador(self.esquema))
        if self.esquema_entrada is not None:
            object.__setattr__(self, "_validador_entrada", _crear_validador(self.esquema_entrada))
        for ejemplo in self.ejemplos:
            try:
                self.datos_entrada(ejemplo.entrada)
            except ValueError:
                raise ValueError(
                    f"La entrada del ejemplo «{ejemplo.nombre}» no cumple el modelo"
                ) from None
            if ejemplo.salida_esperada is not None:
                try:
                    self.validar_salida(ejemplo.salida_esperada)
                except ValueError:
                    raise ValueError(
                        f"La salida esperada del ejemplo «{ejemplo.nombre}» no cumple el esquema"
                    ) from None

    def datos_entrada(self, entrada: Entrada) -> dict[str, Any]:
        if self._validador_entrada is None:
            return entrada.model_dump(exclude_defaults=True)
        if self.campo_texto in entrada.contexto:
            raise ValueError("El contexto no puede redefinir el campo de texto")
        datos = {self.campo_texto: entrada.texto, **entrada.contexto}
        try:
            self._validador_entrada.validate(datos)
        except ValidationError:
            raise ValueError("La entrada no cumple el modelo del tema") from None
        return datos

    def validar_salida(self, salida: Any) -> dict[str, Any]:
        if not isinstance(salida, dict):
            raise ValueError("La salida debe ser un objeto JSON")
        try:
            self._validador.validate(salida)
            json.dumps(salida, allow_nan=False)
        except (ValidationError, Unresolvable, TypeError, ValueError):
            raise ValueError("La salida no cumple el esquema del tema") from None
        return salida


def _leer_bloque_json(contenido: str, nombre: str) -> Any:
    bloque = BLOQUE_JSON.fullmatch(contenido.strip())
    if bloque is None:
        raise ValueError(f"La sección {nombre} debe contener un bloque cercado de JSON")
    try:
        valor = json.loads(bloque[1])
        json.dumps(valor, allow_nan=False)
        return valor
    except ValueError:
        raise ValueError(f"El bloque de la sección {nombre} debe contener JSON válido") from None


def cargar_tema(ruta: Path) -> Tema:
    partes = SECCIONES.split(ruta.read_text(encoding="utf-8"))
    secciones = dict(zip(partes[1::2], partes[2::2], strict=True))
    if len(secciones) != len(partes) // 2:
        raise ValueError("El tema contiene secciones duplicadas")
    if {"Output Model Design", "Input Model Design", "Examples"} & secciones.keys():
        return _cargar_diseno(secciones)
    if not {"Instrucciones", "Esquema"} <= secciones.keys():
        raise ValueError("El tema requiere las secciones Output Model Design e Input Model Design")

    esquema = _leer_bloque_json(secciones["Esquema"], "Esquema")
    ejemplos = ()
    if "Ejemplos" in secciones:
        datos = _leer_bloque_json(secciones["Ejemplos"], "Ejemplos")
        try:
            ejemplos = TypeAdapter(tuple[Ejemplo, ...]).validate_python(datos)
        except ErrorPydantic:
            raise ValueError("La sección Ejemplos debe contener una lista de ejemplos válidos") from None

    return Tema(secciones["Instrucciones"].strip(), esquema, ejemplos)


def _cargar_diseno(secciones: dict[str, str]) -> Tema:
    if not {"Output Model Design", "Input Model Design"} <= secciones.keys():
        raise ValueError("El tema requiere las secciones Output Model Design e Input Model Design")
    salida = leer_modelo(secciones["Output Model Design"], salida=True)
    entrada = leer_modelo(secciones["Input Model Design"], salida=False)
    campo_texto = next(
        (campo for campo in entrada["required"] if entrada["properties"][campo].get("type") == "string"
         and "format" not in entrada["properties"][campo]),
        None,
    )
    if campo_texto is None:
        raise ValueError("Input Model Design debe declarar un campo de texto obligatorio")
    ejemplos = leer_ejemplos(secciones.get("Examples", ""), entrada, salida, campo_texto)
    instrucciones = "\n\n".join(
        f"## {nombre}\n{secciones[nombre].strip()}"
        for nombre in ("Output Model Design", "Input Model Design")
    )
    return Tema(instrucciones, salida, ejemplos, esquema_entrada=entrada, campo_texto=campo_texto)
