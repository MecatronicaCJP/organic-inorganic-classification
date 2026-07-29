/*
  Tesina - Clasificacion de residuos organicos e inorganicos
  Sistemas implementados en este sketch:
    - Sistema de humedad        (DHT22 interno vs DHT22 externo)
    - Sistema capacitivo-inductivo (LJC12A3-5-Z/BY  +  SN04-P)

  Cada sistema se puede ejecutar de DOS formas:
    1) Boton fisico (uno por sistema)
    2) Comando por el monitor serie:  "s1" = humedad , "s2" = capacitivo-inductivo

  Salida:
    - Humedad: humedad interna, externa, la variacion (interna - externa)
               y el resultado organico / inorganico.
    - Cap-ind: el estado individual de cada sensor (activado / no activado)
               y el resultado organico / inorganico (e indica si es metal).
*/

#include "DHT.h"

// ----------------------- Pines -----------------------
#define DHT_INT_PIN   3     // DHT22 interno  (dentro del recipiente de la muestra)
#define DHT_EXT_PIN   2     // DHT22 externo  (ambiente)
#define DHTTYPE       DHT22 // Si el sensor externo fuera un DHT11, crear un type aparte

#define CAP_PIN       8     // sensor capacitivo
#define IND_PIN       9     // sensor inductivo

#define BTN_HUM_PIN   6     // boton -> sistema de humedad      (equivale a "s1")
#define BTN_CAPIND_PIN 7    // boton -> sistema capacitivo-ind. (equivale a "s2")
#define BTN_CAL_PIN   5     // boton -> calibrar/zerar humedad  (equivale a "cal")

// ----------------------- Calibracion -----------------------
// Nivel logico en el que cada sensor se considera "activado".
// El capacitivo (NPN) entrega LOW al detectar -> CAP_ACTIVADO = LOW.
// El inductivo (PNP) entrega HIGH al detectar -> IND_ACTIVADO = HIGH.
// Si en tus pruebas alguno marca al reves, invierte su valor (HIGH <-> LOW).
#define CAP_ACTIVADO LOW
#define IND_ACTIVADO HIGH

// Sistema de humedad: la muestra organica libera humedad, por lo que el sensor
// interno lee mas alto que el externo. Se clasifica organico cuando la diferencia
// (interna - externa), ya compensada, supera el umbral.
//
// La correccion (zerado) se captura EN VIVO con el boton de calibracion: con la
// camara vacia, se mide (interna - externa) y se guarda como linea base, de modo
// que un "sin muestra" quede en ~0. Empieza en 0 hasta la primera calibracion.
float correccionHum = 0.0;          // offset base entre ambos sensores (se setea al calibrar)
const float UMBRAL_HUM = 5.0;       // %HR de diferencia minima para considerar organico

// ----------------------- Objetos / estado -----------------------
DHT dhtInterno(DHT_INT_PIN, DHTTYPE);
DHT dhtExterno(DHT_EXT_PIN, DHTTYPE);

// Estado anterior de cada boton para detectar el flanco (la pulsacion).
int btnHumPrev    = HIGH;
int btnCapIndPrev = HIGH;
int btnCalPrev    = HIGH;

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(50);          // lectura serie no bloqueante (loop atiende los botones)

  pinMode(CAP_PIN, INPUT);
  pinMode(IND_PIN, INPUT);

  // Botones a GND usando la resistencia interna -> reposo = HIGH, pulsado = LOW.
  pinMode(BTN_HUM_PIN,    INPUT_PULLUP);
  pinMode(BTN_CAPIND_PIN, INPUT_PULLUP);
  pinMode(BTN_CAL_PIN,    INPUT_PULLUP);

  dhtInterno.begin();
  dhtExterno.begin();

  Serial.println(F("Sistema listo."));
  Serial.println(F("Comandos: 's1' = humedad , 's2' = capacitivo-inductivo , 'cal' = calibrar humedad"));
  Serial.println(F("Tambien puede usar los botones fisicos."));
  Serial.println(F("Calibre (camara vacia) antes de medir humedad."));
}

void loop() {
  // ---------- 1) Disparo por comando serie ----------
  if (Serial.available() > 0) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();

    if (comando == "s1") {
      sistemaHumedad();
    } else if (comando == "s2") {
      sistemaCapInd();
    } else if (comando == "cal") {
      calibrarHumedad();
    } else if (comando.length() > 0) {
      Serial.print(F("Comando no reconocido: "));
      Serial.println(comando);
    }
  }

  // ---------- 2) Disparo por boton (al presionar) ----------
  int btnHum = digitalRead(BTN_HUM_PIN);
  if (btnHumPrev == HIGH && btnHum == LOW) {   // flanco de bajada = se acaba de presionar
    sistemaHumedad();
    delay(50);                                 // antirrebote simple
  }
  btnHumPrev = btnHum;

  int btnCapInd = digitalRead(BTN_CAPIND_PIN);
  if (btnCapIndPrev == HIGH && btnCapInd == LOW) {
    sistemaCapInd();
    delay(50);
  }
  btnCapIndPrev = btnCapInd;

  int btnCal = digitalRead(BTN_CAL_PIN);
  if (btnCalPrev == HIGH && btnCal == LOW) {
    calibrarHumedad();
    delay(50);
  }
  btnCalPrev = btnCal;
}

// =====================================================
//  Sistema de humedad
// =====================================================
void sistemaHumedad() {
  Serial.println(F("=== Sistema de humedad ==="));

  float humInterna = dhtInterno.readHumidity();
  float humExterna = dhtExterno.readHumidity();

  if (isnan(humInterna) || isnan(humExterna)) {
    Serial.println(F("Error de lectura del/los sensor(es) DHT"));
    return;
  }

  float variacion = humInterna - humExterna;            // cuanto mas humedo esta el interior
  float variacionCal = variacion - correccionHum;       // compensada por el zerado en vivo

  Serial.print(F("Humedad interna: "));  Serial.print(humInterna);  Serial.println(F(" %"));
  Serial.print(F("Humedad externa: "));  Serial.print(humExterna);  Serial.println(F(" %"));
  Serial.print(F("Variacion (int - ext): ")); Serial.print(variacion); Serial.println(F(" %"));
  Serial.print(F("Correccion aplicada: ")); Serial.print(correccionHum); Serial.println(F(" %"));
  Serial.print(F("Variacion neta: ")); Serial.print(variacionCal); Serial.println(F(" %"));

  if (variacionCal > UMBRAL_HUM) {
    Serial.println(F("Resultado: organico"));
  } else {
    Serial.println(F("Resultado: inorganico"));
  }
  Serial.println();
}

// =====================================================
//  Calibracion del sistema de humedad
//  Con la camara VACIA: captura (interna - externa) como linea base.
// =====================================================
void calibrarHumedad() {
  Serial.println(F("=== Calibracion de humedad (camara vacia) ==="));

  float humInterna = dhtInterno.readHumidity();
  float humExterna = dhtExterno.readHumidity();

  if (isnan(humInterna) || isnan(humExterna)) {
    Serial.println(F("Error de lectura: no se pudo calibrar"));
    return;
  }

  correccionHum = humInterna - humExterna;

  Serial.print(F("Humedad interna: ")); Serial.print(humInterna); Serial.println(F(" %"));
  Serial.print(F("Humedad externa: ")); Serial.print(humExterna); Serial.println(F(" %"));
  Serial.print(F("Correccion guardada: ")); Serial.print(correccionHum); Serial.println(F(" %"));
  Serial.println(F("Listo. Ahora coloque la muestra y mida con 's1' o el boton."));
  Serial.println();
}

// =====================================================
//  Sistema capacitivo-inductivo
// =====================================================
void sistemaCapInd() {
  Serial.println(F("=== Sistema capacitivo-inductivo ==="));

  delay(10);  // pequeno tiempo de asentamiento antes de leer
  bool capActivo = (digitalRead(CAP_PIN) == CAP_ACTIVADO);
  bool indActivo = (digitalRead(IND_PIN) == IND_ACTIVADO);

  // Estado individual de cada sensor
  Serial.print(F("Capacitivo: ")); Serial.println(capActivo ? F("ACTIVADO") : F("NO ACTIVADO"));
  Serial.print(F("Inductivo:  ")); Serial.println(indActivo ? F("ACTIVADO") : F("NO ACTIVADO"));

  // Clasificacion:
  //   capacitivo ON + inductivo OFF -> organico
  //   capacitivo ON + inductivo ON  -> metal (inorganico)
  //   capacitivo OFF                -> inorganico (plastico, vidrio, etc.)
  if (capActivo && !indActivo) {
    Serial.println(F("Resultado: organico"));
  } else if (capActivo && indActivo) {
    Serial.println(F("Resultado: inorganico (metal)"));
  } else {
    Serial.println(F("Resultado: inorganico"));
  }
  Serial.println();
}
