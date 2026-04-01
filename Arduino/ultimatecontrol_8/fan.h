#ifndef FAN_H
#define FAN_H

#include <Arduino.h>

enum FanMode {
    FAN_MODE_MANUAL,
    FAN_MODE_NATURAL,
    FAN_MODE_CHAOTIC
};

// Funktionen
void fan_init(uint8_t pin = 4, uint8_t tacho_pin = 5); // Jetzt mit Tacho-Unterstützung
void fan_update();
void fan_set_speed(int percent);
void fan_set_mode(FanMode mode);
void fan_set_min_speed(int percent);
void fan_save_state();
int fan_get_rpm(); // NEU: Um die Drehzahl abzufragen

extern int current_fan_speed;
extern FanMode current_fan_mode;
// fan.h
extern int current_fan_speed;      // Das ist jetzt unser MAX
extern int current_fan_min_speed;  // NEU: Der Boden
#endif