#ifndef circulation_fan_H
#define circulation_fan_H

#include <Arduino.h>

enum circulation_fanMode {
    circulation_fan_MODE_MANUAL,
    circulation_fan_MODE_NATURAL,
    circulation_fan_MODE_CHAOTIC
};

// Funktionen
// In circulation_fan.h
void circulation_fan_init(uint8_t pin, uint8_t tacho_pin);
void circulation_fan_update();
void circulation_fan_set_speed(int percent);
void circulation_fan_set_mode(circulation_fanMode mode);
void circulation_fan_set_min_speed(int percent);
void circulation_fan_save_state();
int circulation_fan_get_rpm(); // NEU: Um die Drehzahl abzufragen

extern int current_circulation_fan_speed;
extern circulation_fanMode current_circulation_fan_mode;
// circulation_fan.h
extern int current_circulation_fan_speed;      // Das ist jetzt unser MAX
extern int current_circulation_fan_min_speed;  // NEU: Der Boden
#endif