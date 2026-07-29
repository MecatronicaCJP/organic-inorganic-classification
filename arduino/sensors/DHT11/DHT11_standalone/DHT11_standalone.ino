#include <DHT.h>

#define DHT_PIN 2
#define DHT_TYPE DHT11

const unsigned long READ_INTERVAL_MS = 2000;

DHT dht(DHT_PIN, DHT_TYPE);
unsigned long lastReadAt = 0;

void setup() {
  Serial.begin(9600);
  dht.begin();

  Serial.println("sensor,temperature_c,humidity_percent");
}

void loop() {
  const unsigned long now = millis();
  if (now - lastReadAt < READ_INTERVAL_MS) {
    return;
  }

  lastReadAt = now;

  const float humidity = dht.readHumidity();
  const float temperatureC = dht.readTemperature();

  if (isnan(humidity) || isnan(temperatureC)) {
    Serial.println("DHT11,error,error");
    return;
  }

  Serial.print("DHT11,");
  Serial.print(temperatureC);
  Serial.print(",");
  Serial.println(humidity);
}
