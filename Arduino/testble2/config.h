#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>


#define PIN_RESET_BUTTON  7  // Den Knopf einfach mit GPIO 4 und GND verbinden
// -------------------- FAN --------------------
#define PIN_CIRC_FAN       45
#define PIN_CIRC_TACHO     2

#define PIN_EXH_FAN        47
#define PIN_EXH_TACHO      1

// -------------------- LIGHT --------------------
#define PIN_LIGHT          21

// -------------------- I2C BUS 0 (SENSORS) --------------------
#define I2C_SDA            4
#define I2C_SCL            5

// -------------------- I2C BUS 1 (RTC + optional SENSOR) --------------------
#define RTC_SDA            13
#define RTC_SCL            14

// -------------------- POWER --------------------
#define PIN_BAT            6

#endif