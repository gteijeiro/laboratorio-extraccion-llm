"""Interfaz de línea de comandos del laboratorio."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from .extractor import ExtractionError, crear_extractor
from .models import Entrada
from .temas import cargar_tema


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extraé datos estructurados con un tema en Markdown")
    parser.add_argument("--tema", required=True, type=Path, help="Ruta al archivo Markdown del tema")
    origen = parser.add_mutually_exclusive_group()
    origen.add_argument("--texto", help="Texto libre para analizar")
    origen.add_argument("--archivo", type=Path, help="Archivo de texto UTF-8 para analizar")
    origen.add_argument("--ejemplos", action="store_true", help="Procesa los ejemplos del tema (modo predeterminado)")
    origen.add_argument("--validar-tema", action="store_true", help="Verifica el tema sin llamar al LLM")
    parser.add_argument("--contexto", help="Objeto JSON con datos adicionales para --texto o --archivo")
    parser.add_argument("--fecha-referencia", help="Fecha ISO 8601 con zona horaria")

    args = parser.parse_args(argv)
    ejemplos = args.texto is None and args.archivo is None
    if args.contexto is not None and ejemplos:
        parser.error("--contexto se usa con --texto o --archivo")

    try:
        tema = cargar_tema(args.tema)
        if args.validar_tema:
            print(f"Tema válido. Ejemplos definidos: {len(tema.ejemplos)}.")
            return 0

        referencia = None
        if args.fecha_referencia is not None:
            referencia = datetime.fromisoformat(args.fecha_referencia)
            if referencia.tzinfo is None or referencia.utcoffset() is None:
                parser.error("--fecha-referencia debe incluir una zona horaria, por ejemplo -03:00")

        if ejemplos:
            if not tema.ejemplos:
                raise ValueError("El tema no incluye ejemplos")
            extractor = crear_extractor(tema)
            salida = [
                {
                    "nombre": ejemplo.nombre,
                    "resultado": extractor.analizar(
                        ejemplo.entrada, fecha_referencia=referencia or ejemplo.fecha_referencia,
                    ),
                }
                for ejemplo in tema.ejemplos
            ]
        else:
            texto = args.archivo.read_text(encoding="utf-8") if args.archivo else args.texto
            contexto = json.loads(args.contexto) if args.contexto is not None else {}
            entrada = Entrada(texto=texto, contexto=contexto)
            extractor = crear_extractor(tema)
            salida = extractor.analizar(entrada, fecha_referencia=referencia)

        print(json.dumps(salida, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except ValidationError:
        print("Error: el texto debe contener datos y el contexto debe ser un objeto JSON.", file=sys.stderr)
        return 1
    except (OSError, ValueError, ExtractionError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
