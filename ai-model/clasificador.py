"""
Clasifica un frame usando el Workflow de Roboflow "proyecto3ro v1 Logic".

Mantiene el mismo contrato de siempre: clasificar(frame) -> (clase, confianza),
asi que main.py no necesita cambiar su logica.
"""

import config
from roboflow_workflow import (
    ErrorRoboflow,          # re-exportado para que main.py pueda atraparlo
    ejecutar_workflow,
    guardar_imagenes,
    mejor_prediccion,
)


def clasificar(frame):
    """
    Recibe un frame de la camara y devuelve (clase, confianza).
    Si la confianza no supera el umbral, devuelve (None, confianza).

    Levanta ErrorRoboflow (o alguna de sus subclases) si falla la llamada.
    """
    salida = ejecutar_workflow(frame)

    if config.GUARDAR_IMAGENES:
        # Las imagenes anotadas se escriben a disco y se sueltan enseguida.
        guardar_imagenes(salida, prefijo="clasificacion")

    clase, confianza = mejor_prediccion(salida)

    if clase is None:
        return None, confianza

    if confianza < config.UMBRAL_CONFIANZA:
        return None, confianza

    return clase, confianza
