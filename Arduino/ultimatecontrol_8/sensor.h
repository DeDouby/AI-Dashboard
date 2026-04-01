#ifndef SENSOR_H
#define SENSOR_H

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_SHT31.h>

#define SENSOR_PIN 1
#define I2C_SDA 2
#define I2C_SCL 3

extern TwoWire I2C_Sensor;
extern Adafruit_SHT31 sht31;
extern bool externalSensorFound;
float getTempIn();
bool initExternalSensor();
float getTempExt();
float getExternalHumidity();

#endif