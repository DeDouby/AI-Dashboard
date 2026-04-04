#ifndef exhaust_fan_H
#define exhaust_fan_H

#include <Arduino.h>

enum exhaust_fanMode {
    exhaust_fan_MODE_MANUAL,
    exhaust_fan_MODE_AUTOMATIC,
    exhaust_fan_MODE_CHAOTIC
};

// Funktionen
void exhaust_fan_init(uint8_t pin, uint8_t tacho_pin);
void exhaust_fan_update();
void exhaust_fan_set_speed(int percent);
void exhaust_fan_set_mode(exhaust_fanMode mode);
void exhaust_fan_set_min_speed(int percent);
void exhaust_fan_save_state();
int exhaust_fan_get_rpm(); // NEU: Um die Drehzahl abzufragen

extern int current_exhaust_fan_speed;
extern exhaust_fanMode current_exhaust_fan_mode;
// exhaust_fan.h
extern int current_exhaust_fan_speed;      // Das ist jetzt unser MAX
extern int current_exhaust_fan_min_speed;  // NEU: Der Boden
#endif