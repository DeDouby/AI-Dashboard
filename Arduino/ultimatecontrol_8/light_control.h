#ifndef LIGHT_CONTROL_H
#define LIGHT_CONTROL_H

#include <Arduino.h>

enum LightMode {
    LIGHT_MODE_OFF_LOCKED = 0, 
    LIGHT_MODE_MANUAL = 1,
    LIGHT_MODE_BREATH = 2,
    LIGHT_MODE_FLICKER = 3,
    LIGHT_MODE_TIMER = 4
};

void light_init(uint8_t pin = 18);
void light_update();
void light_set_brightness(int percent);
void light_set_mode(LightMode mode);
void light_set_timer(int h, int m, int dur);
int light_get_minutes_to_next_change(); // Wieder da!
int light_get_effective_brightness();

extern int current_brightness;
extern LightMode current_light_mode;
extern bool is_light_on_by_timer;

#endif