# Arduino Examples

This folder contains Arduino sketches for testing the sensors used by the
organic/inorganic classification prototype.

## Folder Layout

```text
arduino/
+-- sensors/
|   +-- DHT11/
|       +-- DHT11_standalone/
|           +-- DHT11_standalone.ino
+-- integrated-system/
+-- README.md
```

Add each sensor as a standalone sketch first. After each sensor is verified on
its own, combine the working reads into `integrated-system/`.

## Libraries

Install these libraries with the Arduino IDE Library Manager before compiling
the DHT11 sketch:

- DHT sensor library by Adafruit
- Adafruit Unified Sensor

## Current Pin Map

| Module | Arduino pin | Notes |
|---|---:|---|
| DHT11 data | 2 | Uses a 10k pull-up resistor if the module does not include one |
| DHT11 VCC | 5V | Confirm the module voltage before wiring |
| DHT11 GND | GND | Common ground |

Update this table as capacitive, inductive, and camera communication examples
are added.

## Serial Output

Standalone sketches should print compact comma-separated values so the Python
or web interface can parse readings consistently:

```text
sensor,value_1,value_2
DHT11,24.40,55.00
```
