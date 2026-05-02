#ifndef HARDWARE_INIT_H
#define HARDWARE_INIT_H

#include <Arduino.h>
#include <Wire.h>
#pragma once

extern TwoWire I2C_Sensor;
void init_hardware();
void init_sensor_bus();
void scan_i2c_devices();


void recoverI2C(TwoWire &bus, int sda, int scl);
#endif