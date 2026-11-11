import json
from datetime import datetime
from pathlib import Path
from traceback import format_exception
from unittest.mock import Mock

import pytest

from extraccion_llm.extractor import ExtractionError, Extractor
from extraccion_llm.models import Entrada
from extraccion_llm.temas import cargar_tema

TEMAS = Path(__file__).resolve().parents[1] / "temas"


@pytest.mark.parametrize("archivo", ["seguros.md", "soporte.md"])
def test_mismo_extractor_con_distintos_temas(archivo):
    tema = cargar_tema(TEMAS / archivo)
    ejemplo = tema.ejemplos[0]
    modelo = Mock()
    modelo.invoke.return_value = ejemplo.salida_esperada
    referencia = datetime.fromisoformat("2026-11-11T00:30:00+00:00")

    salida = Extractor(tema, modelo).analizar(ejemplo.entrada, fecha_referencia=referencia)

    assert salida == ejemplo.salida_esperada
    assert salida.keys() == tema.esquema["properties"].keys()
    mensajes = modelo.invoke.call_args.args[0]
    assert mensajes[0][0] == "system"
    assert tema.instrucciones in mensajes[0][1]
    assert "2026-11-10T21:30:00-03:00" in mensajes[0][1]
    assert mensajes[1][0] == "human"
    assert json.loads(mensajes[1][1]) == {
        tema.campo_texto: ejemplo.entrada.texto,
        **ejemplo.entrada.contexto,
    }


def test_rechaza_fecha_sin_zona():
    tema = cargar_tema(TEMAS / "soporte.md")
    modelo = Mock()
    with pytest.raises(ValueError, match="zona horaria"):
        Extractor(tema, modelo).analizar(
            tema.ejemplos[0].entrada, fecha_referencia=datetime(2026, 11, 10),
        )
    modelo.invoke.assert_not_called()


def test_error_del_modelo_no_expone_datos():
    tema = cargar_tema(TEMAS / "soporte.md")
    modelo = Mock()
    modelo.invoke.side_effect = OSError("detalle privado")
    entrada = Entrada(texto="Texto sensible")
    with pytest.raises(ExtractionError, match="No se pudo analizar") as error:
        Extractor(tema, modelo).analizar(entrada)
    mensaje = "".join(format_exception(error.value))
    assert "Texto sensible" not in mensaje
    assert "detalle privado" not in mensaje


def test_salida_de_otro_tema_se_rechaza():
    seguros = cargar_tema(TEMAS / "seguros.md")
    soporte = cargar_tema(TEMAS / "soporte.md")
    modelo = Mock()
    modelo.invoke.return_value = seguros.ejemplos[0].salida_esperada

    with pytest.raises(ExtractionError, match="no cumple el esquema") as error:
        Extractor(soporte, modelo).analizar(soporte.ejemplos[0].entrada)
    assert "paragolpes" not in "".join(format_exception(error.value))
