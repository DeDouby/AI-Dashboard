#include "light_control.h"
#include <time.h>
#include <Preferences.h>

static uint8_t _light_pin = 18;
Preferences lightPrefs;

time_t light_start_unix = 0;
uint32_t light_duration_sec = 43200;
int target_brightness = 50;
uint32_t sunrise_offset_sec = 1800; // NEU: Standard 30 Minuten (30 * 60)
int effective_brightness = 0;

LightMode current_light_mode = LIGHT_MODE_MANUAL;

void light_save_state() {
    lightPrefs.putULong("start_unix", (uint32_t)light_start_unix);
    lightPrefs.putULong("dur_sec", light_duration_sec);
    lightPrefs.putULong("sun_sec", sunrise_offset_sec); // NEU
    lightPrefs.putInt("mode", (int)current_light_mode);
    lightPrefs.putInt("target", target_brightness);
}

void light_init(uint8_t pin) {
    _light_pin = pin;
    ledcAttach(_light_pin, 5000, 8);

    lightPrefs.begin("light", false);

    light_start_unix = (time_t)lightPrefs.getULong("start_unix", 0);
    light_duration_sec = lightPrefs.getULong("dur_sec", 43200);
    sunrise_offset_sec = lightPrefs.getULong("sun_sec", 1800); // NEU
    current_light_mode = (LightMode)lightPrefs.getInt("mode", 1);
    target_brightness = lightPrefs.getInt("target", 50);
}

void light_update() {
    time_t now = time(nullptr);
    struct tm ti_now;
    localtime_r(&now, &ti_now);

    // 1. Aktuelle Sekunden seit Mitternacht berechnen
    int now_sec = ti_now.tm_hour * 3600 + ti_now.tm_min * 60 + ti_now.tm_sec;
    
    bool timer_should_be_on = false;
    uint32_t elapsed_in_window = 0; // Wie lange das Licht im aktuellen Fenster schon an ist

    if (current_light_mode == LIGHT_MODE_TIMER) {
        struct tm ti_start;
        localtime_r(&light_start_unix, &ti_start);
        
        int start_sec = ti_start.tm_hour * 3600 + ti_start.tm_min * 60;
        int dur = light_duration_sec;
        int end_sec = (start_sec + dur); // Hier kein Modulo, wir rechnen absolut

        // Check: Sind wir im Zeitfenster?
        if (start_sec + dur <= 86400) {
            // NORMALFALL (z.B. 08:00 - 20:00)
            if (now_sec >= start_sec && now_sec < end_sec) {
                timer_should_be_on = true;
                elapsed_in_window = now_sec - start_sec;
            }
        } else {
            // ÜBER MITTERNACHT (z.B. 22:00 - 10:00)
            int midnight_end = end_sec % 86400;
            if (now_sec >= start_sec) {
                // Phase 1: Vor Mitternacht (22:00 - 23:59)
                timer_should_be_on = true;
                elapsed_in_window = now_sec - start_sec;
            } else if (now_sec < midnight_end) {
                // Phase 2: Nach Mitternacht (00:00 - 10:00)
                timer_should_be_on = true;
                elapsed_in_window = (86400 - start_sec) + now_sec;
            }
        
        }
    }

    // 2. Helligkeit berechnen
    // In light_update()
    // ... (nach der Zeitberechnung)
    if (current_light_mode == LIGHT_MODE_TIMER) {
        if (timer_should_be_on) {
            if (elapsed_in_window < sunrise_offset_sec) {
                float p = (float)elapsed_in_window / (float)sunrise_offset_sec;
                effective_brightness = 25 + (target_brightness - 25) * p;
            } else {
                effective_brightness = target_brightness;
            }
        } else {
            effective_brightness = 0;
        }
    } 
    else {
        // FIX: In JEDEM anderen Modus (Manuell, Off, etc.) 
        // wird die Helligkeit direkt vom Slider übernommen!
        effective_brightness = target_brightness;
    }

    // PWM Ausgabe
    ledcWrite(_light_pin, map(effective_brightness, 0, 100, 0, 255));
}
int light_get_effective_brightness() {
    return effective_brightness;
}

int light_get_minutes_to_next_change() {
    if (current_light_mode != LIGHT_MODE_TIMER || light_start_unix <= 0) {
        return -1;
    }

    time_t now = time(nullptr);

    struct tm ti_now, ti_start;
    localtime_r(&now, &ti_now);
    localtime_r(&light_start_unix, &ti_start);

    int now_sec = ti_now.tm_hour * 3600 + ti_now.tm_min * 60 + ti_now.tm_sec;
    int start_sec = ti_start.tm_hour * 3600 + ti_start.tm_min * 60;
    int dur = light_duration_sec;
    int end_sec = start_sec + dur;

    // NORMAL (kein Mitternacht-Übergang)
    if (dur <= 86400 && start_sec + dur <= 86400) {
        if (now_sec < start_sec) {
            return (start_sec - now_sec) / 60;
        } else if (now_sec < end_sec) {
            return (end_sec - now_sec) / 60;
        } else {
            return ((86400 - now_sec) + start_sec) / 60;
        }
    } 
    // ÜBER MITTERNACHT
    else {
        int midnight_end = end_sec % 86400;

        if (now_sec >= start_sec) {
            return (end_sec - now_sec) / 60;
        } 
        else if (now_sec < midnight_end) {
            return (midnight_end - now_sec) / 60;
        } 
        else {
            return (start_sec - now_sec) / 60;
        }
    }
}

void light_set_brightness(int p) {
    // Wir setzen nur den Zielwert. 
    // Der Modus (Timer oder Manuell) bleibt einfach so, wie er ist!
    target_brightness = constrain(p, 0, 100);
    
    // Preferences speichern, damit der Wert nach Reboot bleibt
    light_save_state();
    
    // Sofortiges Update der PWM-Ausgabe
    light_update();
}

void light_set_mode(LightMode m) {
    // Wir setzen den neuen Modus
    current_light_mode = m;
    
    // HINWEIS: Wir löschen light_start_unix NICHT auf 0.
    // Warum? Damit der User von MANUELL zurück auf TIMER schalten kann,
    // ohne die Uhrzeit im Overlay neu eintippen zu müssen.
    
    // Falls wir in einen Effekt-Modus gehen (Breath/Flicker), 
    // sorgt light_update() später für die richtige Berechnung.
    
    light_save_state();
    light_update();
}

// In light_control.cpp
void light_set_timer(int h, int m, int d) {
    struct tm ti;
    if (!getLocalTime(&ti)) return;

    ti.tm_hour = h;
    ti.tm_min = m;
    ti.tm_sec = 0;

    light_start_unix = mktime(&ti);
    light_duration_sec = (uint32_t)d * 3600;

    // KEIN sunrise_min hier drin! Die Variable sunrise_offset_sec 
    // wurde bereits vom Webserver aktualisiert.
    
    current_light_mode = LIGHT_MODE_TIMER;

    light_save_state();
    light_update();
}