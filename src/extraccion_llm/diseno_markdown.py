"""Lee las declaraciones y los ejemplos escritos como listas Markdown."""

import json
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from .models import Ejemplo, Entrada

VINETA = re.compile(r"^( *)- +(.*)$")
DECLARACION = re.compile(r"\*\*([^*]+)\*\*\s*\(([^,]+),\s*([^)]+)\):\s*(.*)")
VALOR = re.compile(r"\*\*([^*]+):\*\*\s*(.*)")
EJEMPLO = re.compile(r"^###[ \t]+([^\n]+)$", re.MULTILINE)
ETIQUETA = re.compile(r"^\*\*(Entrada|Salida esperada|Nota):\*\*[ \t]*", re.MULTILINE)
TIPOS = {
    "texto": {"type": "string"},
    "fecha": {"type": "string", "format": "date"},
    "número decimal": {"type": "number"},
    "número entero": {"type": "integer"},
    "booleano": {"type": "boolean"},
}
MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


@dataclass
class Vineta:
    texto: str
    hijos: list["Vineta"] = field(default_factory=list)


def _vinetas(texto: str) -> list[Vineta]:
    raiz: list[Vineta] = []
    niveles = [(-1, raiz)]
    elemento = None
    for linea in texto.expandtabs(4).splitlines():
        vineta = VINETA.fullmatch(linea)
        if vineta is None:
            if elemento is not None and linea.strip() and len(linea) - len(linea.lstrip()) > niveles[-1][0]:
                elemento.texto += " " + linea.strip()
            continue
        sangria = len(vineta[1])
        while niveles[-1][0] >= sangria:
            niveles.pop()
        elemento = Vineta(vineta[2].strip())
        niveles[-1][1].append(elemento)
        niveles.append((sangria, elemento.hijos))
    return raiz


def _objeto(campos: list[Vineta], *, salida: bool) -> dict[str, Any]:
    propiedades = {}
    requeridos = []
    for campo in campos:
        declaracion = DECLARACION.fullmatch(campo.texto)
        if declaracion is None:
            raise ValueError("Los campos del modelo deben tener el formato **campo** (tipo, requisito): descripción")
        nombre, tipo_declarado, requisito, descripcion = declaracion.groups()
        nombre = nombre.strip()
        tipo = tipo_declarado.strip().lower()
        requisito = requisito.strip().lower()
        if not nombre or nombre in propiedades:
            raise ValueError("El modelo contiene un campo vacío o duplicado")
        if requisito not in {"obligatorio", "obligatoria", "opcional"}:
            raise ValueError(f"Requisito inválido para «{nombre}»")

        if tipo == "lista":
            items = _objeto(campo.hijos, salida=salida) if campo.hijos else TIPOS["texto"]
            esquema = {"type": "array", "items": items}
        elif tipo == "objeto" and campo.hijos:
            esquema = _objeto(campo.hijos, salida=salida)
        elif tipo.startswith("texto: ") and not campo.hijos:
            opciones = [opcion.strip() for opcion in tipo_declarado.split(":", 1)[1].split("|")]
            esquema = {"type": "string", "enum": opciones}
        elif tipo in TIPOS and not campo.hijos:
            esquema = TIPOS[tipo].copy()
        else:
            raise ValueError(f"Tipo o subcampos inválidos para «{nombre}»")

        opcional = requisito == "opcional"
        propiedades[nombre] = {"anyOf": [esquema, {"type": "null"}]} if opcional else esquema
        if descripcion:
            propiedades[nombre]["description"] = descripcion
        if salida or not opcional:
            requeridos.append(nombre)
    return {
        "type": "object", "properties": propiedades,
        "required": requeridos, "additionalProperties": False,
    }


def leer_modelo(texto: str, *, salida: bool) -> dict[str, Any]:
    campos = _vinetas(texto)
    if not campos:
        raise ValueError("El modelo debe declarar al menos un campo")
    return _objeto(campos, salida=salida)


def _par(vineta: Vineta) -> tuple[str, str]:
    valor = VALOR.fullmatch(vineta.texto)
    if valor is None:
        raise ValueError("Los valores del ejemplo deben tener el formato **campo:** valor")
    return valor[1].strip(), valor[2].strip()


def _escalar(texto: str, esquema: dict[str, Any]) -> Any:
    if texto == "null":
        return None
    if esquema["type"] == "string" and not (texto.startswith('"') and texto.endswith('"')):
        return texto
    try:
        return json.loads(texto)
    except ValueError:
        raise ValueError("Valor inválido en el ejemplo") from None


def _leer_valor(vineta: Vineta, texto: str, esquema: dict[str, Any], *, salida: bool) -> Any:
    if texto == "null" and not vineta.hijos:
        return None
    tipo = esquema["type"]
    if tipo == "array" and texto == "[]" and not vineta.hijos:
        return []
    if tipo == "object" and not texto:
        return _leer_objeto(vineta.hijos, esquema, salida=salida)
    if tipo == "array" and not texto:
        items = esquema["items"]
        if items["type"] != "object":
            return [_escalar(hijo.texto, items) for hijo in vineta.hijos]
        primer_campo = next(iter(items["properties"]))
        grupos: list[list[Vineta]] = []
        for hijo in vineta.hijos:
            if not grupos or _par(hijo)[0] == primer_campo:
                grupos.append([])
            grupos[-1].append(hijo)
        return [_leer_objeto(grupo, items, salida=salida) for grupo in grupos]
    if vineta.hijos or tipo in {"array", "object"}:
        raise ValueError("Las listas y los objetos del ejemplo deben escribirse con viñetas anidadas")
    return _escalar(texto, esquema)


def _leer_objeto(vinetas: list[Vineta], esquema: dict[str, Any], *, salida: bool) -> dict[str, Any]:
    propiedades = esquema["properties"]
    datos: dict[str, Any] = {}
    for vineta in vinetas:
        nombre, valor = _par(vineta)
        if nombre not in propiedades or nombre in datos:
            raise ValueError(f"Campo no declarado o duplicado en el ejemplo «{nombre}»")
        propiedad = propiedades[nombre]
        if "anyOf" in propiedad and not valor and not vineta.hijos:
            datos[nombre] = None
        else:
            tipo = propiedad["anyOf"][0] if "anyOf" in propiedad else propiedad
            datos[nombre] = _leer_valor(vineta, valor, tipo, salida=salida)
    if salida:
        for nombre, propiedad in propiedades.items():
            if "anyOf" in propiedad:
                datos.setdefault(nombre, None)
    return datos


def _fecha_de_nota(nota: str) -> date | None:
    referencia = re.search(r"\b(?:referencia|se recibi[oó])\b(.*)", nota, re.IGNORECASE | re.DOTALL)
    if referencia is None:
        return None
    iso = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", referencia[1])
    if iso:
        return date.fromisoformat(iso[1])
    fecha = re.search(
        r"\b(\d{1,2}) de (" + "|".join(MESES) + r") de (\d{4})\b",
        referencia[1], re.IGNORECASE,
    )
    if fecha:
        dia, mes, anio = fecha.groups()
        return date(int(anio), MESES.index(mes.lower()) + 1, int(dia))
    return None


def leer_ejemplos(
    texto: str, entrada: dict[str, Any], salida: dict[str, Any], campo_texto: str
) -> tuple[Ejemplo, ...]:
    partes = EJEMPLO.split(texto)
    ejemplos = []
    for nombre, cuerpo in zip(partes[1::2], partes[2::2], strict=True):
        bloques = ETIQUETA.split(cuerpo)
        secciones = dict(zip(bloques[1::2], bloques[2::2], strict=True))
        if len(secciones) != len(bloques) // 2 or "Entrada" not in secciones:
            raise ValueError(f"El ejemplo «{nombre}» debe incluir una Entrada y etiquetas únicas")
        datos = _leer_objeto(_vinetas(secciones["Entrada"]), entrada, salida=False)
        relato = datos.pop(campo_texto, None)
        if not isinstance(relato, str) or not relato.strip():
            raise ValueError(f"Falta texto en la entrada del ejemplo «{nombre}»")
        esperada = (
            _leer_objeto(_vinetas(secciones["Salida esperada"]), salida, salida=True)
            if "Salida esperada" in secciones else None
        )
        ejemplos.append(Ejemplo(
            nombre=nombre.strip(),
            entrada=Entrada(texto=relato, contexto=datos),
            salida_esperada=esperada,
            fecha_referencia=_fecha_de_nota(secciones.get("Nota", "")),
        ))
    if not ejemplos and texto.strip():
        raise ValueError("Cada ejemplo debe comenzar con un encabezado de nivel 3")
    return tuple(ejemplos)
