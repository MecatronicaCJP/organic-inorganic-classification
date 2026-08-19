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


def leer_serial(arduino, buffer):
    """
    Lee el serial sin bloquear y separa dos cosas:
      - el marcador MARCADOR_CLASIFICAR (boton del pin 4) -> dispara la camara
      - cualquier otra linea (humedad, cap-inductivo, calibracion) -> se muestra
        en la consola, asi no hace falta abrir el Serial Monitor.
    Devuelve (disparo, lineas_sensores, buffer_actualizado).
    """
    if arduino is None:
        return False, [], buffer
    try:
        if arduino.in_waiting:
            buffer += arduino.read(arduino.in_waiting).decode("utf-8", errors="ignore")
    except Exception:
        return False, [], buffer

    disparo = False
    lineas = []
    while "\n" in buffer:
        linea, buffer = buffer.split("\n", 1)
        linea = linea.strip()
        if not linea:
            continue
        if linea == config.MARCADOR_CLASIFICAR:
            disparo = True
        else:
            lineas.append(linea)
    return disparo, lineas, buffer


def enviar_comando(arduino, comando):
    """Manda un comando al Arduino (s1 / s2 / cal), igual que el monitor serie."""
    if arduino is None:
        print(f"(sin Arduino conectado: no se puede enviar '{comando}')")
        return
    try:
        arduino.write((comando + "\n").encode())
        print(f">> comando enviado al Arduino: {comando}")
    except Exception as e:
        print("No se pudo enviar el comando:", e)


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

    texto = "ESPACIO o boton (pin 4) = clasificar"
    color = BLANCO
    ayuda = "ESPACIO/boton=camara | 1=hum 2=cap-ind 3=calib | Q=salir"

    print("Sistema iniciado. Coloca el residuo frente a la camara.")
    print("Teclas: ESPACIO o boton pin 4 = camara | 1 = humedad | "
          "2 = capacitivo-inductivo | 3 = calibrar | Q = salir")
    print("Los resultados de los sensores aparecen aca como [Arduino].")

    while True:
        ok, frame = cam.read()
        if not ok:
            print("ERROR: no se pudo leer el frame.")
            break

        # Se dibuja sobre una copia para no ensuciar la imagen original
        vista = frame.copy()
        cv2.putText(vista, texto, (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(vista, ayuda, (10, vista.shape[0] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, BLANCO, 1)
        cv2.imshow("Clasificacion de residuos", vista)

        tecla = cv2.waitKey(espera) & 0xFF

        # El boton del pin 4 dispara la camara; el resto de las lineas son los
        # resultados de los otros sistemas y se imprimen aca (no hace falta el
        # Serial Monitor, que ademas no podria abrir el puerto al mismo tiempo).
        disparo_boton, lineas_arduino, buffer_serial = leer_serial(arduino, buffer_serial)
        for linea in lineas_arduino:
            print("[Arduino]", linea)

        if tecla == ord(' ') or disparo_boton:
            texto, color = clasificar_y_formatear(frame)
            print(texto)

        elif tecla == ord('1'):
            enviar_comando(arduino, "s1")    # sistema de humedad
        elif tecla == ord('2'):
            enviar_comando(arduino, "s2")    # sistema capacitivo-inductivo
        elif tecla == ord('3'):
            enviar_comando(arduino, "cal")   # calibrar humedad (camara vacia)

        elif tecla == ord('q'):
            break

    cam.release()
    cv2.destroyAllWindows()
    if arduino is not None:
        arduino.close()
    print("Sistema finalizado.")


if __name__ == "__main__":
    main()
