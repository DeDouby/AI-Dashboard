///////////////////////////////////////////////////////////////////////////////
// !!! ABSOLUTES GESETZ: DAS TARGET-REVISION-PRINZIP (C++ / ESP32) !!!
// -------------------------------------------------------------------------
// 1. HARDWARE FOLGT TARGET: Die Loop darf NIEMALS direkt auf UI-Inputs reagieren.
//    Sie vergleicht permanent: 'target_val' vs 'effective_val'.
//
// 2. REVISION-CONFIRMATION: Der ESP32 bestätigt eine Änderung NUR, indem er 
//    die empfangene 'rev' (Revision) im Status-Paket unverändert zurücksendet.
//
// 3. KEINE LÜGEN: Der Status 'Synced' (Grün in der App) darf NUR dann entstehen,
//    wenn 'esp32_rev' == 'ui_target_rev'.
//
// 4. ATOMARE UPDATES: Bei Empfang eines neuen Targets wird die 'rev' sofort 
//    gespeichert, aber der 'effective_val' zieht (ggf. über Rampen) stur nach.
//
// JEDE KI-ÄNDERUNG MUSS DIESE ASYNCHRONE LOGIK WAHREN. DIREKTES ÜBERSCHREIBEN
// VON PINS OHNE TARGET-ABGLEICH IST EIN SYSTEMFEHLER!
///////////////////////////////////////////////////////////////////////////////
#include "exhaust_fan.h"
#include <Preferences.h>
#include "sensor.h"

static uint8_t _exhaust_fan_pin;
static uint8_t _tacho_pin; 
Preferences exhaust_fanPrefs;

// Definitionen ohne 'static' damit sie 'extern' funktionieren
int current_exhaust_fan_speed = 60;
exhaust_fanMode current_exhaust_fan_mode = exhaust_fan_MODE_AUTOMATIC;
int current_exhaust_fan_min_speed = 20; 
int target_exhaust_fan_pct = 60;

int exhaust_fan_min = 20;
int exhaust_fan_pct = 60;

int target_temp_min = 22;
int target_temp_max = 28;
int target_humidity_min = 40;
int target_humidity_max = 70;

float target_temp = 26.0;
float target_humidity = 60.0;
// Neue globale Variablen (neben den anderen target_xxx)
float target_vpd_min = 0.8f;
float target_vpd_max = 1.5f;

volatile int exhaust_fan_pulse_count = 0; 
static uint32_t last_exhaust_fan_rpm_check = 0;
static int current_exhaust_fan_rpm = 0;
static uint32_t last_exhaust_fan_pulse_time = 0;
static uint32_t exhaust_fan_rev = 0;     // ← NEU: Eigenes Rev für Exhaust Fan
static uint32_t exhaust_fan_init_rev = 0;

void IRAM_ATTR count_exhaust_fan_pulse() {
    uint32_t now = micros();
    if (now - last_exhaust_fan_pulse_time > 2000) { 
        exhaust_fan_pulse_count++;
        last_exhaust_fan_pulse_time = now;
    }
}

void exhaust_fan_save_state() {
    exhaust_fanPrefs.putInt("min_p", exhaust_fan_min);
    exhaust_fanPrefs.putInt("max_p", exhaust_fan_pct);
    exhaust_fanPrefs.putInt("mode", (int)current_exhaust_fan_mode);
    exhaust_fanPrefs.putInt("t_min", target_temp_min);
    exhaust_fanPrefs.putInt("t_max", target_temp_max);
    exhaust_fanPrefs.putInt("h_min", target_humidity_min);
    exhaust_fanPrefs.putInt("h_max", target_humidity_max);
    exhaust_fanPrefs.putFloat("vpd_min", target_vpd_min);
    exhaust_fanPrefs.putFloat("vpd_max", target_vpd_max);
}

void exhaust_fan_init(uint8_t pin, uint8_t tacho_pin) {
    _exhaust_fan_pin = pin;
    _tacho_pin = tacho_pin;
    ledcAttach(_exhaust_fan_pin, 25000, 8); 
    
    exhaust_fanPrefs.begin("exhaust_fan", false);
    exhaust_fan_min = exhaust_fanPrefs.getInt("min_p", 20);
    exhaust_fan_pct = exhaust_fanPrefs.getInt("max_p", 60);
    current_exhaust_fan_mode = (exhaust_fanMode)exhaust_fanPrefs.getInt("mode", 1); 
    target_temp_min = exhaust_fanPrefs.getInt("t_min", 22);
    target_temp_max = exhaust_fanPrefs.getInt("t_max", 28);
    target_humidity_min = exhaust_fanPrefs.getInt("h_min", 40);
    target_humidity_max = exhaust_fanPrefs.getInt("h_max", 70);
    target_vpd_min = exhaust_fanPrefs.getFloat("vpd_min", 0.8f);
    target_vpd_max = exhaust_fanPrefs.getFloat("vpd_max", 1.5f);
    if (_tacho_pin != 255) {
        pinMode(_tacho_pin, INPUT_PULLUP);
        attachInterrupt(digitalPinToInterrupt(_tacho_pin), count_exhaust_fan_pulse, FALLING);
    }
    exhaust_fan_set_mode(current_exhaust_fan_mode);
    exhaust_fan_init_rev = millis() + 1;

}

void exhaust_fan_set_speed(int percent) {
    exhaust_fan_pct = constrain(percent, 0, 100);
    exhaust_fan_save_state();
}

void exhaust_fan_set_mode(exhaust_fanMode mode) {
    current_exhaust_fan_mode = mode;
    exhaust_fan_save_state();
}

void exhaust_fan_set_min_speed(int percent) {
    exhaust_fan_min = constrain(percent, 0, 100);
    exhaust_fan_save_state();
}

int exhaust_fan_get_rpm() {
    uint32_t now = millis();
    if (now - last_exhaust_fan_rpm_check >= 1000) {
        noInterrupts();
        uint32_t pulses = exhaust_fan_pulse_count;
        exhaust_fan_pulse_count = 0;
        interrupts();
        current_exhaust_fan_rpm = (pulses * 60) / 2;
        last_exhaust_fan_rpm_check = now;
    }
    return current_exhaust_fan_rpm;
}

void exhaust_fan_update() {
    // MANUAL MODE
    if (current_exhaust_fan_mode == exhaust_fan_MODE_MANUAL) {

        current_exhaust_fan_speed = exhaust_fan_pct;   // ✅ zuerst setzen

        uint32_t duty;
        if (current_exhaust_fan_speed <= 0) {
            duty = 0;
        } else {
            duty = map(current_exhaust_fan_speed, 1, 100, 0, 255);
        }

        ledcWrite(_exhaust_fan_pin, duty);
        return;
    }

    static uint32_t last_wind_change = 0;
    if (millis() - last_wind_change > 1500) {
        float mix_factor = 0;

        if (current_exhaust_fan_mode == exhaust_fan_MODE_AUTOMATIC) {
            float temp = getTempExt();
            float hum  = getExternalHumidity();
            if (temp <= -250.0 || hum <= -250.0) return;

            float t_f = 0.0f;
            float h_f = 0.0f;

            if (temp > target_temp_max) {
                float over = temp - target_temp_max;
                t_f = constrain(over / 10.0f, 0.0f, 1.0f);
            }

            if (hum > target_humidity_max) {
                float over = hum - target_humidity_max;
                h_f = constrain(over / 20.0f, 0.0f, 1.0f);
            }

            t_f = t_f * t_f;
            h_f = h_f * h_f;

            mix_factor = max(t_f, h_f);
        } 
        else if (current_exhaust_fan_mode == exhaust_fan_MODE_CHAOTIC) {
            mix_factor = random(0, 101) / 100.0;
        }

        int fan_range = max(0, exhaust_fan_pct - exhaust_fan_min);

        int computed = exhaust_fan_min + (int)(fan_range * mix_factor);

        if (mix_factor <= 0.01f) {
            computed = (exhaust_fan_min == 0) ? 0 : exhaust_fan_min;
        }

        if (computed < exhaust_fan_min) {
            computed = exhaust_fan_min;
        }

        current_exhaust_fan_speed = computed;

        uint32_t duty;
        if (current_exhaust_fan_speed <= 0) {
            duty = 0;
        } else {
            duty = map(current_exhaust_fan_speed, 1, 100, 0, 255);
        }

        ledcWrite(_exhaust_fan_pin, duty);

        last_wind_change = millis();
    }

}

// Füge dies am Ende deiner exhaust_fan.cpp hinzu
void exhaust_fan_process_json(JsonObject doc) {
    bool changed = false;
    uint32_t received_rev = 0;

    if (doc.containsKey("rev_exhaust")) {        // ← NEU: eigener Key
        received_rev = doc["rev_exhaust"];
    }

    // Nur verarbeiten, wenn die Revision wirklich neu ist
    if (received_rev > exhaust_fan_rev) {

        exhaust_fan_rev = received_rev;

        // 1. Fan Speed & Min
        if (doc.containsKey("exhaust_fan_pct")) {
            exhaust_fan_pct = constrain((int)doc["exhaust_fan_pct"], 0, 100);
            changed = true;
        }
        if (doc.containsKey("exhaust_fan_min")) {
            exhaust_fan_min = constrain((int)doc["exhaust_fan_min"], 0, 100);
            changed = true;
        }

        // 2. Mode
        if (doc.containsKey("exhaust_fan_mode")) {
            String m = doc["exhaust_fan_mode"];
            if (m == "auto") current_exhaust_fan_mode = exhaust_fan_MODE_AUTOMATIC;
            else if (m == "chao") current_exhaust_fan_mode = exhaust_fan_MODE_CHAOTIC;
            else current_exhaust_fan_mode = exhaust_fan_MODE_MANUAL;
            changed = true;
        }

        // 3. Targets (Temp, Humidity, VPD)
        if (doc.containsKey("target_temp_min")) {
            target_temp_min = constrain((int)doc["target_temp_min"], 15, 35);
            changed = true;
        }
        if (doc.containsKey("target_temp_max")) {
            target_temp_max = constrain((int)doc["target_temp_max"], 15, 35);
            changed = true;
        }
        if (doc.containsKey("target_humidity_min")) {
            target_humidity_min = constrain((int)doc["target_humidity_min"], 0, 100);
            changed = true;
        }
        if (doc.containsKey("target_humidity_max")) {
            target_humidity_max = constrain((int)doc["target_humidity_max"], 0, 100);
            changed = true;
        }
        if (doc.containsKey("target_vpd_min")) {
            target_vpd_min = constrain((float)doc["target_vpd_min"], 0.0f, 3.0f);
            changed = true;
        }
        if (doc.containsKey("target_vpd_max")) {
            target_vpd_max = constrain((float)doc["target_vpd_max"], 0.0f, 3.0f);
            changed = true;
        }
    }

    if (changed) {
        exhaust_fan_save_state();
        if (current_exhaust_fan_mode == exhaust_fan_MODE_MANUAL) {
            exhaust_fan_update();
        }
        Serial.printf("Exhaust Fan updated | Rev: %u\n", exhaust_fan_rev);
    }
}
void exhaust_fan_get_status(JsonObject doc) {
    doc["exhaust_fan_rpm"] = exhaust_fan_get_rpm();
    doc["exhaust_fan_pct"] = exhaust_fan_pct;
    doc["exhaust_fan_min"] = exhaust_fan_min;
    doc["exhaust_fan_speed_now"] = current_exhaust_fan_speed;
    doc["exhaust_fan_mode"] = (current_exhaust_fan_mode == exhaust_fan_MODE_AUTOMATIC) ? "auto" : 
                             (current_exhaust_fan_mode == exhaust_fan_MODE_CHAOTIC) ? "chao" : "man";
    doc["target_temp_min"] = target_temp_min;
    doc["target_temp_max"] = target_temp_max;
    doc["target_humidity_min"] = target_humidity_min;
    doc["target_humidity_max"] = target_humidity_max;
    doc["target_vpd_min"] = target_vpd_min;
    doc["target_vpd_max"] = target_vpd_max;
    
    doc["rev_exhaust"] = exhaust_fan_rev;        // ← WICHTIG: Eigenes Rev zurücksenden
    doc["rev_init_exhaust"] = exhaust_fan_init_rev;
}