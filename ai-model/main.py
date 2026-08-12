import cv2
import config
from clasificador import clasificar
from roboflow_workflow import ErrorConfiguracion, ErrorRoboflow

try:
    import serial  # pyserial (para el boton fisico del Arduino)
except ImportError:
    serial = None

# Colores en formato BGR (asi los usa OpenCV)
VERDE   = (0, 255, 0)
AZUL    = (255, 100, 0)
NARANJA = (0, 165, 255)
ROJO    = (0, 0, 255)
BLANCO  = (255, 255, 255)


def abrir_arduino():
    """
    Abre el puerto serie del Arduino para escuchar el boton del pin 4.
    Si algo falla (sin pyserial, sin puerto, Arduino desconectado), avisa y
    devuelve None: el sistema sigue andando solo con la tecla ESPACIO.
    """
    if not config.PUERTO_ARDUINO:
        return None
    if serial is None:
        print("Aviso: falta 'pyserial', el boton fisico no va a funcionar (solo ESPACIO).")
        print("       Instalalo con:  pip install pyserial")
        return None
    try:
        ard = serial.Serial(config.PUERTO_ARDUINO, config.BAUD_ARDUINO, timeout=0)
        print(f"Arduino conectado en {config.PUERTO_ARDUINO}: boton del pin 4 activo.")
        return ard
    except Exception as e:
        print(f"Aviso: no se pudo abrir {config.PUERTO_ARDUINO} ({e}).")
        print("       Revisa el puerto en config.py. Por ahora solo funcionara ESPACIO.")
        return None


def leer_trigger_boton(arduino, buffer):
    """
    Lee el serial sin bloquear y detecta la linea MARCADOR_CLASIFICAR.
    Ignora cualquier otro texto (por ej. los mensajes de los sensores).
    Devuelve (disparo, buffer_actualizado).
    """
    if arduino is None:
        return False, buffer
    try:
        if arduino.in_waiting:
            buffer += arduino.read(arduino.in_waiting).decode("utf-8", errors="ignore")
    except Exception:
        return False, buffer

    disparo = False
    while "\n" in buffer:
        linea, buffer = buffer.split("\n", 1)
        if linea.strip() == config.MARCADOR_CLASIFICAR:
            disparo = True
    return disparo, buffer


def clasificar_y_formatear(frame):
    """Corre la clasificacion y devuelve (texto, color) listo para mostrar."""
    try:
        clase, conf = clasificar(frame)

        if clase is None:
            return f"NO IDENTIFICADO ({conf:.0f}%)", NARANJA
        elif clase.lower().startswith("org"):
            return f"ORGANICO ({conf:.0f}%)", VERDE
        else:
            return f"INORGANICO ({conf:.0f}%)", AZUL

    except ErrorConfiguracion as e:
        print("Error de configuracion:", e)
        return "FALTA LA API KEY", ROJO
    except ErrorRoboflow as e:
        print("Error al clasificar:", e)
        return "ERROR DE CONEXION", ROJO
    except Exception as e:
        print("Error inesperado al clasificar:", e)
        return "ERROR INESPERADO", ROJO


def main():
    if not config.API_KEY:
        print("ERROR: falta la variable de entorno ROBOFLOW_API_KEY.")
        print("Consegui la clave en https://app.roboflow.com/settings/api")
        print('Linux/Mac:  export ROBOFLOW_API_KEY="tu_clave"')
        print('Windows:    setx ROBOFLOW_API_KEY "tu_clave"  (y abri una consola nueva)')
        return

    cam = cv2.VideoCapture(config.CAMARA)

    if not cam.isOpened():
        print("ERROR: no se pudo abrir la camara.")
        print("Proba cambiando CAMARA a 1 en config.py")
        return

    cam.set(cv2.CAP_PROP_FRAME_WIDTH, config.ANCHO)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, config.ALTO)
    cam.set(cv2.CAP_PROP_FPS, config.FPS)
    # Sin buffer no se acumulan frames viejos al leer despacio
    cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    espera = max(1, int(1000 / config.FPS))

    arduino = abrir_arduino()
    buffer_serial = ""

    texto = "ESPACIO o boton (pin 4) = clasificar   |   Q = salir"
    color = BLANCO

    print("Sistema iniciado. Coloca el residuo frente a la camara.")

    while True:
        ok, frame = cam.read()
        if not ok:
            print("ERROR: no se pudo leer el frame.")
            break

        # Se dibuja sobre una copia para no ensuciar la imagen original
        vista = frame.copy()
        cv2.putText(vista, texto, (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.imshow("Clasificacion de residuos", vista)

        tecla = cv2.waitKey(espera) & 0xFF

        # El boton del pin 4 dispara exactamente lo mismo que la barra espaciadora
        disparo_boton, buffer_serial = leer_trigger_boton(arduino, buffer_serial)

        if tecla == ord(' ') or disparo_boton:
            texto, color = clasificar_y_formatear(frame)
            print(texto)

        elif tecla == ord('q'):
            break

    cam.release()
    cv2.destroyAllWindows()
    if arduino is not None:
        arduino.close()
    print("Sistema finalizado.")


if __name__ == "__main__":
    main()
