"""
Cliente del Workflow de Roboflow "proyecto3ro v1 Logic".

Este modulo NO asume los nombres de salida del workflow. Lee lo que venga
y busca de forma generica las predicciones y las imagenes en base64.
Para ver las claves reales, corre:  python inspeccionar_workflow.py
"""

from __future__ import annotations

import base64
import binascii
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturoVencido
from pathlib import Path

import config


# --- Errores propios ---------------------------------------------------------

class ErrorRoboflow(Exception):
    """Error generico de la integracion con Roboflow."""


class ErrorConfiguracion(ErrorRoboflow):
    """Falta la API key o algun dato de configuracion."""


class ErrorConexion(ErrorRoboflow):
    """No se pudo hablar con el servidor (timeout, red caida, error 5xx)."""


class ErrorRespuesta(ErrorRoboflow):
    """El servidor respondio, pero con algo que no podemos usar."""


# --- Cliente -----------------------------------------------------------------

_cliente = None
# Varios workers a proposito: si una llamada queda colgada, la siguiente
# no se tiene que quedar esperando en la cola detras de ella.
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="roboflow")


def _obtener_cliente():
    """Crea el InferenceHTTPClient una sola vez y lo reutiliza."""
    global _cliente

    if _cliente is not None:
        return _cliente

    if not config.API_KEY:
        raise ErrorConfiguracion(
            "Falta la API key. Defini la variable de entorno ROBOFLOW_API_KEY "
            "con la clave de https://app.roboflow.com/settings/api"
        )

    # Import adentro para que las funciones de parseo se puedan probar
    # sin tener instalado el SDK.
    from inference_sdk import InferenceHTTPClient

    _cliente = InferenceHTTPClient(
        api_url=config.API_URL,
        api_key=config.API_KEY,
    )
    return _cliente


def _codigo_http(error):
    """Devuelve el status code del error si el SDK lo expone, si no None."""
    for atributo in ("status_code", "code"):
        valor = getattr(error, atributo, None)
        if isinstance(valor, int):
            return valor
    return None


def ejecutar_workflow(imagen, parametros=None):
    """
    Corre el workflow sobre UNA imagen y devuelve el dict de salida.

    imagen     : ruta a un archivo, URL https, o un frame de OpenCV (numpy).
    parametros : dict con los parametros declarados por el workflow.
                 El workflow solo declara la entrada 'image', asi que
                 normalmente va en None.

    Devuelve el primer (y unico) elemento de la lista de resultados, que es
    un dict con las claves que define el propio workflow.

    Levanta ErrorConfiguracion, ErrorConexion o ErrorRespuesta.
    """
    cliente = _obtener_cliente()

    argumentos = {
        "workspace_name": config.WORKSPACE_NAME,
        "workflow_id": config.WORKFLOW_ID,
        "images": {config.NOMBRE_ENTRADA_IMAGEN: imagen},
    }
    if parametros:
        argumentos["parameters"] = parametros

    ultimo_error = None

    for intento in range(config.REINTENTOS + 1):
        try:
            # El SDK no expone un timeout por request, asi que lo cortamos
            # desde afuera. El hilo puede seguir un rato, pero el programa
            # (la ventana de OpenCV) no se queda colgado.
            futuro = _pool.submit(cliente.run_workflow, **argumentos)
            resultado = futuro.result(timeout=config.TIMEOUT)

        except FuturoVencido as error:
            ultimo_error = ErrorConexion(
                f"El workflow no respondio en {config.TIMEOUT} segundos."
            )

        except Exception as error:
            codigo = _codigo_http(error)

            # 4xx = problema nuestro (key mala, workflow inexistente,
            # imagen invalida). Reintentar no sirve de nada.
            if codigo is not None and 400 <= codigo < 500:
                raise ErrorRespuesta(
                    f"Roboflow rechazo la peticion (HTTP {codigo}): {error}"
                ) from error

            ultimo_error = ErrorConexion(f"Fallo la llamada a Roboflow: {error}")

        else:
            if not isinstance(resultado, list) or not resultado:
                raise ErrorRespuesta(
                    f"Se esperaba una lista con al menos un resultado, "
                    f"llego: {type(resultado).__name__}"
                )

            salida = resultado[0]
            if not isinstance(salida, dict):
                raise ErrorRespuesta(
                    f"Se esperaba un dict de salidas, llego: {type(salida).__name__}"
                )
            return salida

        if intento < config.REINTENTOS:
            time.sleep(config.ESPERA_REINTENTO * (2 ** intento))

    raise ultimo_error


# --- Lectura defensiva de la respuesta ---------------------------------------

# Solo guardamos estos campos de cada prediccion. Se descartan a proposito
# 'points' (poligonos de segmentacion) y 'mask', que pesan muchisimo.
CAMPOS_UTILES = ("class", "class_id", "confidence", "x", "y", "width", "height")


def _limpiar_prediccion(prediccion):
    """Se queda solo con los campos livianos de una prediccion."""
    return {k: prediccion[k] for k in CAMPOS_UTILES if k in prediccion}


def _predicciones_de(valor):
    """
    Extrae una lista de predicciones de cualquier forma razonable:
    una lista suelta, o un dict con la clave 'predictions'.
    """
    if isinstance(valor, dict):
        valor = valor.get("predictions", [])

    if not isinstance(valor, list):
        return []

    return [
        _limpiar_prediccion(p)
        for p in valor
        if isinstance(p, dict) and "confidence" in p
    ]


def extraer_predicciones(salida):
    """
    Recorre TODAS las claves de la salida y junta las predicciones que
    encuentre, sin importar como se llame el bloque en el workflow.
    """
    encontradas = []
    for valor in salida.values():
        encontradas.extend(_predicciones_de(valor))
    return encontradas


def mejor_prediccion(salida):
    """
    Devuelve (clase, confianza_en_porcentaje) de la prediccion mas confiable.
    Si no hay ninguna, devuelve (None, 0.0).
    """
    predicciones = extraer_predicciones(salida)
    if not predicciones:
        return None, 0.0

    mejor = max(predicciones, key=lambda p: p.get("confidence", 0.0))
    clase = mejor.get("class")
    confianza = float(mejor.get("confidence", 0.0)) * 100
    return clase, confianza


# --- Imagenes de salida ------------------------------------------------------

_PREFIJOS_IMAGEN = ("/9j/", "iVBOR", "R0lGOD", "UklGR")  # jpeg, png, gif, webp


def _texto_base64_de(valor):
    """
    Devuelve el string base64 si el valor parece una imagen, si no None.
    Acepta tanto un string suelto como {'type': 'base64', 'value': '...'}.
    """
    if isinstance(valor, dict):
        if valor.get("type") == "base64":
            valor = valor.get("value")
        else:
            return None

    if not isinstance(valor, str) or len(valor) < 100:
        return None

    if valor.startswith("data:image"):
        valor = valor.split(",", 1)[-1]

    return valor if valor[:8].lstrip().startswith(_PREFIJOS_IMAGEN) else None


def guardar_imagenes(salida, prefijo="salida"):
    """
    Decodifica las salidas de tipo imagen y las escribe en disco.
    Devuelve la lista de rutas creadas.

    Las imagenes vienen en base64 y pesan cientos de KB: se escriben y se
    sueltan enseguida, nunca se imprimen ni se guardan en memoria.
    """
    carpeta = Path(config.CARPETA_SALIDA)
    carpeta.mkdir(parents=True, exist_ok=True)

    rutas = []
    marca = time.strftime("%Y%m%d-%H%M%S")

    for nombre, valor in salida.items():
        texto = _texto_base64_de(valor)
        if texto is None:
            continue

        try:
            crudo = base64.b64decode(texto, validate=True)
        except (binascii.Error, ValueError):
            continue

        ruta = carpeta / f"{prefijo}_{marca}_{nombre}.jpg"
        ruta.write_bytes(crudo)
        rutas.append(ruta)
        del crudo

    return rutas


def resumen_de_claves(salida):
    """
    Describe la forma de la salida SIN volcar el contenido.
    Util para debug y para el smoke test.
    """
    resumen = {}
    for nombre, valor in salida.items():
        if _texto_base64_de(valor) is not None:
            resumen[nombre] = "imagen (base64)"
        elif _predicciones_de(valor):
            resumen[nombre] = f"predicciones ({len(_predicciones_de(valor))})"
        else:
            resumen[nombre] = type(valor).__name__
    return resumen
