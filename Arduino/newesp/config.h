#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// --- LÜFTER PINS ---
#define PIN_CIRC_FAN       8
#define PIN_CIRC_TACHO     9

#define PIN_EXH_FAN        4
#define PIN_EXH_TACHO      7

// --- LICHT PINS ---
#define PIN_LIGHT          21

// --- SENSOR / I2C ---
#define SENSOR_PIN         1
#define I2C_SDA            16
#define I2C_SCL            17


// --- I2C BUS 2: RTC (NEU) ---
#define RTC_SDA            13 // Anpassen falls belegt!
#define RTC_SCL            14 // Anpassen falls belegt!
// --- POWER ---
#define PIN_BAT            5

#endif