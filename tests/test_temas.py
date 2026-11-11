import json
from datetime import date
from pathlib import Path
from unittest.mock import Mock

import pytest

from extraccion_llm import cli
from extraccion_llm.extractor import Extractor
from extraccion_llm.temas import cargar_tema

TEMAS = Path(__file__).resolve().parents[1] / "temas"


def test_rechaza_fecha_invalida_y_campos_extra_en_objetos_anidados():
    tema = cargar_tema(TEMAS / "seguros.md")
    salida = tema.ejemplos[0].salida_esperada
    with pytest.raises(ValueError, match="no cumple"):
        tema.validar_salida({**salida, "fecha_incidente": "2026-02-30"})
    with pytest.raises(ValueError, match="no cumple"):
        tema.validar_salida({
            **salida,
            "danios_afectados": [{"descripcion": "Faro", "importe_estimado": None, "extra": True}],
        })


def test_admite_un_tema_nuevo_sin_tocar_python(tmp_path, capsys, monkeypatch):
    tema = tmp_path / "recetas.md"
    tema.write_text(
        "# Recetas\n\n## Instrucciones\nExtraé el nombre del plato.\n\n"
        '## Esquema\n```json\n{"type":"object","properties":{"plato":{"type":"string"}},'
        '"required":["plato"],"additionalProperties":false}\n```\n',
        encoding="utf-8",
    )

    def crear_extractor(perfil):
        assert set(perfil.esquema["properties"]) == {"plato"}
        from extraccion_llm.extractor import Extractor

        class Modelo:
            def invoke(self, mensajes):
                assert json.loads(mensajes[1][1])["texto"] == "Hoy comimos locro."
                return {"plato": "locro"}

        return Extractor(perfil, Modelo())

    monkeypatch.setattr(cli, "crear_extractor", crear_extractor)
    entrada = tmp_path / "entrada.txt"
    entrada.write_text("Hoy comimos locro.", encoding="utf-8")
    assert cli.main(["--tema", str(tema), "--archivo", str(entrada)]) == 0
    assert json.loads(capsys.readouterr().out) == {"plato": "locro"}


def test_validar_tema_sin_crear_proveedor(capsys, monkeypatch):
    def proveedor_inesperado(_):
        pytest.fail("Validar el tema no debe iniciar un proveedor")

    monkeypatch.setattr(cli, "crear_extractor", proveedor_inesperado)
    assert cli.main(["--tema", str(TEMAS / "seguros.md"), "--validar-tema"]) == 0
    assert "Ejemplos definidos: 2" in capsys.readouterr().out


def test_cli_toma_los_reclamos_y_la_nota_del_markdown(capsys, monkeypatch):
    modelo = Mock()

    def crear_extractor(tema):
        modelo.invoke.side_effect = [ejemplo.salida_esperada for ejemplo in tema.ejemplos]
        assert tema.ejemplos[1].fecha_referencia == date(2026, 11, 10)
        return Extractor(tema, modelo)

    monkeypatch.setattr(cli, "crear_extractor", crear_extractor)
    assert cli.main(["--tema", str(TEMAS / "seguros.md")]) == 0
    resultados = json.loads(capsys.readouterr().out)
    assert [item["nombre"] for item in resultados] == [
        "Ejemplo 1: Accidente de tránsito", "Ejemplo 2: Daño por agua en vivienda",
    ]
    assert resultados[0]["resultado"]["danios_afectados"] == [
        {"descripcion": "Paragolpes delantero dañado", "importe_estimado": None},
        {"descripcion": "Faro izquierdo dañado", "importe_estimado": None},
    ]
    mensajes = modelo.invoke.call_args_list[1].args[0]
    assert "Referencia temporal: 2026-11-10\n" in mensajes[0][1]
    entrada = json.loads(mensajes[1][1])
    assert entrada["texto_reclamacion"].startswith("Ayer se rompió una cañería")
    assert entrada["numero_poliza"] == "HOG-67890"
    assert entrada["nombre_cliente"] == "María Gómez"


def test_rechaza_ejemplo_con_salida_ajena_al_esquema(tmp_path):
    texto = (TEMAS / "soporte.md").read_text(encoding="utf-8")
    tema = tmp_path / "tema.md"
    tema.write_text(texto.replace('**categoria:** "acceso"', '**categoria:** "otra"'), encoding="utf-8")
    with pytest.raises(ValueError, match="salida esperada"):
        cargar_tema(tema)
