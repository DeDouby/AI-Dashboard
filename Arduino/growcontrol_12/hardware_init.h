#ifndef HARDWARE_INIT_H
#define HARDWARE_INIT_H

#include <Arduino.h>
#include <Wire.h>
extern int global_brightness_percent;
extern TwoWire I2C_Sensor;
void init_hardware();
void init_display();
void init_touch();
void init_backlight();
void init_sensor_bus();
void scan_i2c_devices();

#endif