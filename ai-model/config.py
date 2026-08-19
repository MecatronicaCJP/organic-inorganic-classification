import os

# --- Datos de Roboflow ---
# La API key NUNCA va escrita aca. Se lee de una variable de entorno.
#   Linux/Mac:  export ROBOFLOW_API_KEY="tu_clave"
#   Windows:    setx ROBOFLOW_API_KEY "tu_clave"
# La clave esta en https://app.roboflow.com/settings/api
API_KEY = os.environ.get("ROBOFLOW_API_KEY", "")

# --- Workflow "proyecto3ro v1 Logic" ---
API_URL = "https://serverless.roboflow.com"
WORKSPACE_NAME = "enzotakeo9999-gmail-com"
WORKFLOW_ID = "proyecto3ro-v1-logic"
NOMBRE_ENTRADA_IMAGEN = "image"   # unica entrada declarada por el workflow

# --- Configuracion del sistema ---
UMBRAL_CONFIANZA = 60   # % minimo para dar una respuesta
CAMARA = 0              # 0 = webcam integrada, 1 = webcam externa

# --- Arduino (boton fisico del pin 4 que dispara la clasificacion) ---
# En Mac el puerto suele ser /dev/cu.usbserial-XXXX o /dev/cu.usbmodemXXXX
#   (con el Arduino conectado, ver con:  ls /dev/cu.* )
# En Windows es un COM (ej. "COM3"). Deja "" para desactivar el boton (solo ESPACIO).
PUERTO_ARDUINO = "/dev/cu.usbserial-1430"
BAUD_ARDUINO = 9600                 # debe coincidir con Serial.begin() del sketch
MARCADOR_CLASIFICAR = "CLASIFICAR"  # linea que manda el Arduino al apretar el boton pin 4

# --- Rendimiento (bajar si la compu se traba) ---
FPS = 10                # cuadros por segundo que se leen y muestran
ANCHO = 640             # resolucion de captura
ALTO = 480

# --- Red ---
TIMEOUT = 30            # segundos maximos de espera por respuesta
REINTENTOS = 2          # reintentos ante fallas de red o errores 5xx
ESPERA_REINTENTO = 1.0  # segundos base, se duplica en cada reintento

# --- Salidas del workflow ---
CARPETA_SALIDA = "salidas"   # donde se guardan las imagenes que devuelve
GUARDAR_IMAGENES = False     # True para escribir a disco cada clasificacion
