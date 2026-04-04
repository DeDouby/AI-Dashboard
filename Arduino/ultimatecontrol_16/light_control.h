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

// INITIALISIERUNG
// Wir nehmen den Parameter raus, da PIN_LIGHT aus config.h kommt
void light_init(); 

// CONTROL & UPDATE
void light_update();
void light_set_brightness(int percent);
void light_set_mode(LightMode mode);
void light_set_timer(int h, int m, int dur);

// GETTER (Für Webserver / UI)
int light_get_minutes_to_next_change(); 
int light_get_effective_brightness();

// EXTERNALS (Damit der Webserver diese Variablen sieht)
// WICHTIG: Die Namen müssen exakt so lauten wie in der .cpp Datei!
extern int target_brightness; 
extern LightMode current_light_mode;

#endif