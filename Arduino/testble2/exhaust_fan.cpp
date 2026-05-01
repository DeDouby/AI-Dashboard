// !!! ABSOLUTES GESETZ: DAS TARGET-REVISION-PRINZIP (v2.0) !!!
// -------------------------------------------------------------------------
// 1. HARDWARE FOLGT TARGET: Loop reagiert nur auf target_val vs effective_val.
//    Direktes Pin-Schreiben durch UI-Input ist streng verboten!
//
// 2. HANDSHAKE (rev_init): Beim Öffnen des Overlays wird eine rev_init gesendet.
//    Der ESP spiegelt diese NUR im RAM. Dies erzwingt ein Status-Update und
//    bestätigt die Verbindung ("Alive-Check"), OHNE den Flash zu belasten.
//
// 3. REVISION-CONFIRMATION (rev): Der ESP bestätigt ECHTE Änderungen (Werte),
//    indem er die rev spiegelt. Erst dann wird der Flash-Speicher (Save) aktiv.
//
// 4. KEINE LÜGEN: Das UI zeigt "Synced" (Grün) NUR, wenn:
//    (ui_init == esp_init) UND (ui_rev == esp_rev).
//
// 5. ATOMARE UPDATES: Neue Revisionen werden sofort übernommen, die Hardware
//    (effective_val) zieht asynchron (ggf. über Rampen) nach.
//
// JEDE KI-ÄNDERUNG MUSS DIESE TRENNUNG VON RAM-PING (INIT) UND FLASH-DATA (REV)
// WAHREN. WERTE OHNE REVISIONS-SPIEGELUNG SIND REINE LÜGEN!
///////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////
#include "exhaust_fan.h"
#include <Preferences.h>
#include "sensor.h"
#include "light_control.h"
#include "ble_scanner.h"
static uint8_t _exhaust_fan_pin;
static uint8_t _tacho_pin; 
Preferences exhaust_fanPrefs;
#define EXHAUST_FAILSAFE_MIN 55
// Definitionen ohne 'static' damit sie 'extern' funktionieren
int current_exhaust_fan_speed = 60;
exhaust_fanMode current_exhaust_fan_mode = exhaust_fan_MODE_AUTOMATIC;
int current_exhaust_fan_min_speed = 20; 
int target_exhaust_fan_pct = 60;

int exhaust_fan_min = 20;
int exhaust_fan_pct = 60;

// Von int auf float ändern
float target_temp_min = 22.0f;
float target_temp_max = 28.0f;
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
static uint32_t target_over_threshold_start = 0; 
static float persistence_boost = 0.0f;           
static float temp_trend = 0.0f;
static float hum_trend = 0.0f;
static float last_temp_h = -255.0f;
static float last_hum_h = -255.0f;
static uint32_t last_trend_check = 0;
static uint32_t efficiency_test_start = 0;
static bool efficiency_test_active = false;
static float temp_before_test = 0.0f;
static uint32_t last_wind_change = 0;
static uint32_t last_rev_seen = 0;
static uint32_t last_warn_msg = 0; // Neu: Damit die Konsole nicht zugespamt wird
// Ganz oben bei den anderen globalen Variablen einfügen:
bool exhaust_fan_chaos_active = false;

enum PlantPhase {
    DAY_TRANSPIRE,
    EVENING_TRANSITION,
    NIGHT_RECOVERY,
    MORNING_WAKEUP
};

PlantPhase getPlantPhase() {

    int light = light_get_effective_brightness();
    int remaining = light_get_minutes_to_next_change();

    // Nacht = Licht aus + lange Phase
    if (light == 0) return NIGHT_RECOVERY;

    // Übergänge
    if (remaining != -1 && remaining < 60) {
        return EVENING_TRANSITION;
    }

    if (light > 80) {
        return DAY_TRANSPIRE;
    }

    return DAY_TRANSPIRE;
}



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
    exhaust_fanPrefs.putFloat("t_min", target_temp_min);
    exhaust_fanPrefs.putFloat("t_max", target_temp_max);
    exhaust_fanPrefs.putInt("h_min", target_humidity_min);
    exhaust_fanPrefs.putInt("h_max", target_humidity_max);
    exhaust_fanPrefs.putFloat("vpd_min", target_vpd_min);
    exhaust_fanPrefs.putFloat("vpd_max", target_vpd_max);
    exhaust_fanPrefs.putBool("chao_active", exhaust_fan_chaos_active);
}
void reset_exhaust_logic() {
    // Trends
    temp_trend = 0.0f;
    hum_trend = 0.0f;

    // Historie
    last_temp_h = -255.0f;
    last_hum_h  = -255.0f;
    last_trend_check = 0;

    // Threshold / Persistence
    target_over_threshold_start = 0;
    persistence_boost = 0.0f;

    // Efficiency Guard
    efficiency_test_active = false;
    efficiency_test_start = 0;
    temp_before_test = 0.0f;
}
void exhaust_fan_init(uint8_t pin, uint8_t tacho_pin) {
    _exhaust_fan_pin = pin;
    _tacho_pin = tacho_pin;
    ledcAttach(_exhaust_fan_pin, 5000, 8);
    
    exhaust_fanPrefs.begin("exhaust_fan", false);
    
    // Basiseinstellungen
    exhaust_fan_min = exhaust_fanPrefs.getInt("min_p", 20);
    exhaust_fan_pct = exhaust_fanPrefs.getInt("max_p", 60);
    current_exhaust_fan_mode = (exhaust_fanMode)exhaust_fanPrefs.getInt("mode", 1); 

    // TARGETS - Hier war der Fehler: putFloat braucht getFloat!
    target_temp_min = exhaust_fanPrefs.getFloat("t_min", 22.0f);
    target_temp_max = exhaust_fanPrefs.getFloat("t_max", 28.0f);
    
    target_humidity_min = exhaust_fanPrefs.getInt("h_min", 40);
    target_humidity_max = exhaust_fanPrefs.getInt("h_max", 70);

    // VPD - Fehlte beim Laden komplett
    target_vpd_min = exhaust_fanPrefs.getFloat("vpd_min", 0.8f);
    target_vpd_max = exhaust_fanPrefs.getFloat("vpd_max", 1.5f);

    if (_tacho_pin != 255) {
        pinMode(_tacho_pin, INPUT_PULLUP);
        attachInterrupt(digitalPinToInterrupt(_tacho_pin), count_exhaust_fan_pulse, RISING);
    }
    exhaust_fan_chaos_active = exhaust_fanPrefs.getBool("chao_active", false);
    exhaust_fan_set_mode(current_exhaust_fan_mode);
    exhaust_fan_rev = millis();
    // Handshake Initialisierung
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

        int new_rpm = (pulses * 60) / 4; // 2 Pulse pro Umdrehung
        // Glättung: 70% alter Wert, 30% neuer Wert (verhindert Springen)
        current_exhaust_fan_rpm = (current_exhaust_fan_rpm * 0.7f) + (new_rpm * 0.3f);
        
        last_exhaust_fan_rpm_check = now;
    }
    return current_exhaust_fan_rpm;
}
void exhaust_fan_update() {
    uint32_t now = millis();
    static uint32_t last_wind_change = 0;
    static uint32_t last_rev_seen = 0;

    // 1. REVISION-CHECK (Sofortige Reaktion bei UI-Änderung)
    if (last_rev_seen != exhaust_fan_rev) {
        last_rev_seen = exhaust_fan_rev;
        last_wind_change = 0; 
        reset_exhaust_logic(); 
    }

    if (now - last_wind_change < 1500 && last_wind_change != 0) return;
    last_wind_change = now;

    float final_pct = 0.0f;

    // ============================================================
    // SCHRITT A: BASIS-WERT ERMITTELN
    // ============================================================
    if (current_exhaust_fan_mode == exhaust_fan_MODE_MANUAL) {
        // Basis ist der Reglerwert aus dem UI
        final_pct = (float)exhaust_fan_pct;
    } 
    else {
        // Basis ist die Sensor-Logik (Auto)
        float in_temp = getTempExt();
        float in_hum  = getExternalHumidity();
        float mix_factor = 0.0f;

        if (in_temp > -250.0f && in_hum > -250.0f) {
            float t_f = constrain((in_temp - target_temp_max) / 5.0f, 0.0f, 1.0f);
            float h_f = constrain((in_hum - target_humidity_max) / 10.0f, 0.0f, 1.0f);
            mix_factor = max(t_f, h_f);

            PlantPhase phase = getPlantPhase();
            if (phase == NIGHT_RECOVERY) mix_factor *= 0.55f;
            else if (phase == EVENING_TRANSITION) mix_factor *= 0.75f;
        }

        int fan_range = exhaust_fan_pct - exhaust_fan_min;
        final_pct = (float)exhaust_fan_min + (fan_range * mix_factor);
    }

    // ============================================================
    // SCHRITT B: CHAOS ÜBERSTÜLPEN (Egal ob Auto oder Manuell)
    // ============================================================
    if (exhaust_fan_chaos_active) {
        // Wir erzeugen eine Schwankung von ca. +/- 15%
        float wobble = (float)random(-15, 16);
        final_pct += wobble;
    }

    // ============================================================
    // SCHRITT C: SCHUTZFUNKTIONEN (NUR für Auto!)
    // ============================================================
    if (current_exhaust_fan_mode == exhaust_fan_MODE_AUTOMATIC) {
        float in_temp = getTempExt();
        float in_hum  = getExternalHumidity();
        float out_temp = BLEScanner::get_sps_temp();
        float out_hum  = BLEScanner::get_sps_hum();
        bool out_ok    = BLEScanner::is_sps_online();

        // Wenn Außenluft schlechter ist, greift der Failsafe (min. 55%)
        bool outside_bad = out_ok && (out_temp > in_temp + 0.5f || out_hum > in_hum + 3.0f);
        int failsafe = max((int)EXHAUST_FAILSAFE_MIN, exhaust_fan_min);

        if (outside_bad && final_pct < (float)failsafe) {
            final_pct = (float)failsafe;
        }
    }

    // ============================================================
    // SCHRITT D: HARDWARE-OUTPUT
    // ============================================================
    current_exhaust_fan_speed = constrain((int)final_pct, 0, 100);
    ledcWrite(_exhaust_fan_pin, map(current_exhaust_fan_speed, 0, 100, 0, 255));
}
void exhaust_fan_process_json(JsonObject doc) {
    bool flash_changed = false;

    // 1. HANDSHAKE (RAM ONLY)
    if (doc.containsKey("rev_init_exhaust")) {
        exhaust_fan_init_rev = doc["rev_init_exhaust"];
    }

    // 2. DATEN-REVISION (FLASH RELEVANT)
    if (doc.containsKey("rev_exhaust")) {
        uint32_t received_rev = doc["rev_exhaust"];

        if (received_rev > exhaust_fan_rev) {
            exhaust_fan_rev = received_rev;

            // --- CHAOS FLAG (Der neue Trigger) ---
            // Wir prüfen, ob das UI das Chaos-Flag mitschickt
            if (doc.containsKey("exhaust_fan_chaos")) {
                exhaust_fan_chaos_active = doc["exhaust_fan_chaos"];
                // Da wir das Chaos-Flag im UI toggeln wollen, speichern wir es mit
                flash_changed = true; 
            }

            // --- FAN SPEED & MIN ---
            if (doc.containsKey("exhaust_fan_pct")) {
                exhaust_fan_pct = constrain((int)doc["exhaust_fan_pct"], 0, 100);
                flash_changed = true;
            }
            if (doc.containsKey("exhaust_fan_min")) {
                exhaust_fan_min = constrain((int)doc["exhaust_fan_min"], 0, 100);
                flash_changed = true;
            }

            // --- MODUS (AUTO / MAN) ---
            if (doc.containsKey("exhaust_fan_mode")) {
                String m = doc["exhaust_fan_mode"];
                if (m == "auto") current_exhaust_fan_mode = exhaust_fan_MODE_AUTOMATIC;
                else current_exhaust_fan_mode = exhaust_fan_MODE_MANUAL;
                // 'chao' als eigenständigen Modus brauchen wir nicht mehr, 
                // da es jetzt ein paralleles Flag ist!
                flash_changed = true;
            }

            // --- TARGETS (TEMP/HUM/VPD) ---
            if (doc.containsKey("target_temp_min")) { target_temp_min = constrain((float)doc["target_temp_min"], 15, 35); flash_changed = true; }
            if (doc.containsKey("target_temp_max")) { target_temp_max = constrain((float)doc["target_temp_max"], 15, 35); flash_changed = true; }
            if (doc.containsKey("target_humidity_min")) { target_humidity_min = constrain((int)doc["target_humidity_min"], 0, 100); flash_changed = true; }
            if (doc.containsKey("target_humidity_max")) { target_humidity_max = constrain((int)doc["target_humidity_max"], 0, 100); flash_changed = true; }
            if (doc.containsKey("target_vpd_min")) { target_vpd_min = constrain((float)doc["target_vpd_min"], 0.0f, 3.0f); flash_changed = true; }
            if (doc.containsKey("target_vpd_max")) { target_vpd_max = constrain((float)doc["target_vpd_max"], 0.0f, 3.0f); flash_changed = true; }
        }
    }

    // 3. SPEICHERN & UPDATE
    if (flash_changed) {
        // Wir müssen das Chaos-Flag auch in die Preferences schreiben!
        exhaust_fanPrefs.putBool("chao_active", exhaust_fan_chaos_active);
        exhaust_fan_save_state();
        reset_exhaust_logic(); 
        Serial.printf("Exhaust Update | Rev: %u | Chaos: %s\n", exhaust_fan_rev, exhaust_fan_chaos_active ? "ON" : "OFF");
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
    doc["plant_phase"] = getPlantPhase();
    doc["exhaust_fan_chaos_active"] = exhaust_fan_chaos_active;
}