#ifndef SENSOR_H
#define SENSOR_H

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_SHT31.h>



extern TwoWire I2C_Sensor;
extern Adafruit_SHT31 sht31;
extern bool externalSensorFound;
float getTempIn();
bool initExternalSensor();
float getTempExt();
float getExternalHumidity();

#endif