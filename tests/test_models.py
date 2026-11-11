import pytest
from pydantic import ValidationError

from extraccion_llm.models import Entrada


@pytest.mark.parametrize("texto", ["", " \n "])
def test_rechaza_entradas_vacias(texto):
    with pytest.raises(ValidationError):
        Entrada(texto=texto)


def test_entrada_admite_contexto_arbitrario():
    entrada = Entrada(texto="Texto", contexto={"id": 123, "etiquetas": ["a", "b"]})
    assert entrada.model_dump() == {
        "texto": "Texto", "contexto": {"id": 123, "etiquetas": ["a", "b"]},
    }
