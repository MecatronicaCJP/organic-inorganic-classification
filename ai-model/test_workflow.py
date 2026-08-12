"""
Smoke test de la integracion con Roboflow.

    python test_workflow.py ruta/a/una/foto.jpg

Comprueba que:
  1. la llamada al workflow responde un dict de salidas,
  2. estan presentes las claves que quedaron registradas por
     inspeccionar_workflow.py en salidas/claves_esperadas.json,
  3. las funciones de parseo devuelven algo usable.

Tambien anda con pytest si algun dia lo agregas al proyecto, usando la
imagen de la variable de entorno IMAGEN_DE_PRUEBA.
"""

import json
import os
import sys
from pathlib import Path

import config
from roboflow_workflow import (
    ejecutar_workflow,
    extraer_predicciones,
    mejor_prediccion,
    resumen_de_claves,
)

ARCHIVO_CLAVES = Path(config.CARPETA_SALIDA) / "claves_esperadas.json"


def imagen_de_prueba():
    if len(sys.argv) > 1:
        return sys.argv[1]
    return os.environ.get("IMAGEN_DE_PRUEBA", "")


def test_workflow_responde_las_claves_esperadas():
    imagen = imagen_de_prueba()
    assert imagen, (
        "Pasa una imagen: python test_workflow.py foto.jpg "
        "(o defini IMAGEN_DE_PRUEBA)"
    )
    assert config.API_KEY, "Falta la variable de entorno ROBOFLOW_API_KEY"

    salida = ejecutar_workflow(imagen)

    assert isinstance(salida, dict), f"Se esperaba dict, llego {type(salida)}"
    assert salida, "El workflow devolvio una salida vacia"

    if ARCHIVO_CLAVES.exists():
        esperadas = set(json.loads(ARCHIVO_CLAVES.read_text(encoding="utf-8")))
        faltantes = esperadas - set(salida.keys())
        assert not faltantes, f"Faltan claves de salida: {sorted(faltantes)}"
    else:
        print(
            f"AVISO: no existe {ARCHIVO_CLAVES}. "
            "Corre inspeccionar_workflow.py para registrar las claves reales."
        )

    # El parseo no debe explotar, aunque no haya detecciones en la foto.
    predicciones = extraer_predicciones(salida)
    assert isinstance(predicciones, list)
    for p in predicciones:
        assert "points" not in p, "No hay que arrastrar poligonos de segmentacion"

    clase, confianza = mejor_prediccion(salida)
    assert clase is None or isinstance(clase, str)
    assert 0.0 <= confianza <= 100.0

    return salida, clase, confianza


def main():
    try:
        salida, clase, confianza = test_workflow_responde_las_claves_esperadas()
    except AssertionError as error:
        print("FALLO:", error)
        return 1
    except Exception as error:
        print(f"FALLO ({type(error).__name__}):", error)
        return 1

    print("Salidas del workflow:")
    for nombre, forma in resumen_de_claves(salida).items():
        print(f"  {nombre}: {forma}")

    print(f"\nMejor prediccion: {clase} ({confianza:.1f}%)")
    print("\nOK: smoke test paso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
