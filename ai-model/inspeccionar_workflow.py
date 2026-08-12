"""
Grounding: muestra la definicion real del workflow y la forma real de su
respuesta. Corre esto UNA vez antes de confiar en la integracion.

    python inspeccionar_workflow.py ruta/a/una/foto.jpg

Guarda las claves de salida en salidas/claves_esperadas.json, que es lo que
despues usa el smoke test (test_workflow.py) para verificar.
"""

import json
import sys
from pathlib import Path

import requests

import config
from roboflow_workflow import ejecutar_workflow, resumen_de_claves

ARCHIVO_CLAVES = Path(config.CARPETA_SALIDA) / "claves_esperadas.json"


def mostrar_definicion():
    """Pide la definicion del workflow a la API de Roboflow (best effort)."""
    url = (
        f"https://api.roboflow.com/{config.WORKSPACE_NAME}"
        f"/workflows/{config.WORKFLOW_ID}"
    )
    try:
        respuesta = requests.get(
            url, params={"api_key": config.API_KEY}, timeout=config.TIMEOUT
        )
        respuesta.raise_for_status()
        definicion = respuesta.json()
    except Exception as error:
        print(f"(No se pudo leer la definicion: {error})")
        print("No importa: la corrida real de abajo es la fuente de verdad.\n")
        return

    # La definicion puede venir anidada segun la version de la API.
    especificacion = definicion
    for clave in ("workflow", "specification"):
        if isinstance(especificacion, dict) and clave in especificacion:
            especificacion = especificacion[clave]
    if isinstance(especificacion, str):
        especificacion = json.loads(especificacion)

    if not isinstance(especificacion, dict):
        return

    for seccion in ("inputs", "parameters", "outputs"):
        contenido = especificacion.get(seccion)
        if contenido:
            print(f"--- {seccion} ---")
            print(json.dumps(contenido, indent=2, ensure_ascii=False))
            print()


def main():
    if not config.API_KEY:
        print("ERROR: falta la variable de entorno ROBOFLOW_API_KEY.")
        return 1

    if len(sys.argv) < 2:
        print("Uso: python inspeccionar_workflow.py ruta/a/una/foto.jpg")
        print("(tambien sirve una URL https de una imagen)")
        return 1

    imagen = sys.argv[1]

    print(f"Workflow: {config.WORKSPACE_NAME}/{config.WORKFLOW_ID}\n")
    mostrar_definicion()

    print("--- corrida real ---")
    salida = ejecutar_workflow(imagen)

    resumen = resumen_de_claves(salida)
    for nombre, forma in resumen.items():
        print(f"  {nombre}: {forma}")

    ARCHIVO_CLAVES.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVO_CLAVES.write_text(
        json.dumps(sorted(salida.keys()), indent=2), encoding="utf-8"
    )
    print(f"\nClaves guardadas en {ARCHIVO_CLAVES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
