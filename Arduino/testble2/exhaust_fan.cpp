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
#include <time.h>
#include "ble_scanner.h"
#include "light_control.h"

static uint8_t _exhaust_fan_pin;
static uint8_t _tacho_pin; 
static uint32_t failsafe_phase = 0;
static PlantPhase current_phase = DAY_TRANSPIRE;
Preferences exhaust_fanPrefs;
#define EXHAUST_FAILSAFE_MIN 33
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
static String exhaust_fan_state_reason = "day_auto";
static bool vpd_control_enabled = true; // für zukünftige UI-Steuerung
// Ganz oben bei den anderen globalen Variablen einfügen:
bool exhaust_fan_chaos_active = false;

// In der ISR: Wir bleiben bei den Zeitabständen, machen sie aber präziser
void IRAM_ATTR count_exhaust_fan_pulse() {
    uint32_t now = micros();
    uint32_t delta = now - last_exhaust_fan_pulse_time;

    // Ein Lüfter mit 4 Pulsen schafft physikalisch selten mehr als 5000 RPM.
    // 5000 RPM bei 4 Pulsen = 3ms pro Puls. 
    // Alles, was schneller als 2.5ms (2500µs) kommt, MUSS Rauschen sein.
    if (delta > 2500) { 
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
    uint32_t elapsed = now - last_exhaust_fan_rpm_check;

    if (elapsed >= 1000) {
        noInterrupts();
        uint32_t pulses = exhaust_fan_pulse_count;
        exhaust_fan_pulse_count = 0;
        interrupts();

        // DEIN GESETZ: Teiler 4. Berechnung basierend auf echtem Zeit-Delta:
        float pulses_per_rev = 4.0f;
        int calculated_rpm = (int)((pulses / pulses_per_rev) * (60000.0f / elapsed));

        // Plausibilitäts-Filter:
        // Wenn der neue Wert mehr als 50% vom alten abweicht (bei hohen Drehzahlen),
        // ist es wahrscheinlich ein Glitch. Wir dämpfen das extrem.
        if (current_exhaust_fan_rpm > 500 && calculated_rpm > current_exhaust_fan_rpm * 1.5f) {
            calculated_rpm = current_exhaust_fan_rpm + 50; // Nur sanfter Anstieg erlaubt
        }

        // Glättung für das UI (80% alt, 20% neu)
        current_exhaust_fan_rpm = (current_exhaust_fan_rpm * 0.8f) + (calculated_rpm * 0.2f);
        
        last_exhaust_fan_rpm_check = now;
    }
    return current_exhaust_fan_rpm;
}
// Hilfsfunktion: Berechnet VPD in kPa
float calculate_current_vpd(float temp, float hum) {
    if (temp < -50.0f || hum < 0.0f) return 1.0f; // Failsafe
    
    // Sättigungsdampfdruck (SVP) in kPa
    float svp = 0.61078f * exp((17.27f * temp) / (temp + 237.3f));
    // Tatsächlicher Dampfdruck (AVP)
    float avp = svp * (hum / 100.0f);
    
    // VPD ist die Differenz
    return svp - avp;
}
// Hilfsfunktion zur Schätzung der Zielfeuchte nach Erwärmung
float estimate_refined_humidity(float temp_out, float hum_out, float temp_target) {
    if (temp_out >= temp_target) return hum_out; // Keine Veredelung durch Wärme möglich
    
    // Vereinfachte Magnus-Formel Näherung: 
    // Pro 1°C Erwärmung sinkt die rel. Feuchte um ca. 5% vom aktuellen Wert
    // Genauer: Sättigungsdampfdruck steigt, dadurch sinkt rel. Feuchte.
    float temp_diff = temp_target - temp_out;
    float refined_hum = hum_out * pow(0.945f, temp_diff); 
    return constrain(refined_hum, 0.0f, 100.0f);
}

void exhaust_fan_update() {
    uint32_t now = millis();
    static uint32_t last_wind_change = 0;
    static uint32_t last_rev_seen = 0;
    
    // ============================================================
    // 1. REVISION & TIMING CHECK
    // ============================================================
    if (last_rev_seen != exhaust_fan_rev) {
        last_rev_seen = exhaust_fan_rev;
        last_wind_change = 0;
        reset_exhaust_logic();
    }

    if (now - last_wind_change < 1500 && last_wind_change != 0) return;
    last_wind_change = now;

    float final_pct = 0.0f;
    bool is_manual = (current_exhaust_fan_mode == exhaust_fan_MODE_MANUAL);
    
    
    PlantPhase phase = getPlantPhase();
        
    // KRITISCH:
    // IMMER setzen.
    // Nicht nur im else!
    current_phase = phase;
    
    
    float in_temp = getTempExt();
    float in_hum  = getExternalHumidity();
    float out_temp = BLEScanner::get_sps_temp();
    float out_hum  = BLEScanner::get_sps_hum();
    bool out_ok    = BLEScanner::is_sps_online();

    // ============================================================
    // 2. VEREDELUNGS-ANALYSE (THERMODYNAMIK)
    // ============================================================
    bool air_can_be_refined = false;
    if (out_ok && out_temp < target_temp_max) {
        // Wie feucht wäre die Außenluft, wenn sie auf unsere Ziel-Temp erwärmt wird?
        float potential_hum = estimate_refined_humidity(out_temp, out_hum, target_temp_max);
        
        // Wenn die Luft nach Erwärmung unter unser Feuchte-Target fällt -> TOP!
        if (potential_hum <= (float)target_humidity_max) {
            air_can_be_refined = true;
        }
    }


    // ============================================================
    // 3. BASIS-REGELUNG (TEMP, HUM & VPD) WITH SENSOR FAILSAFE
    // ============================================================
    if (is_manual) {
        final_pct = (float)exhaust_fan_pct;
        exhaust_fan_state_reason = "manual";
    } 
    else {
        bool sensors_valid = (in_temp > -200.0f && in_hum > -200.0f);

        if (sensors_valid) {
            float mix_factor = 0.0f;
            
            // A: Temperatur-Stress (immer aktiv)
            float t_f = constrain((in_temp - target_temp_max) / 3.0f, 0.0f, 1.0f);
            
            // B: Feuchtigkeits-Stress (immer aktiv)
            float h_f = constrain((in_hum - (float)target_humidity_max) / 10.0f, 0.0f, 1.0f);
            
            // C: VPD-Stress → NUR bei Licht!
            float vpd_f = 0.0f;
            bool vpd_active = false;

            // VPD nur aktiv während Lichtphase (inkl. Rampen)
            if (phase == DAY_TRANSPIRE || 
                phase == MORNING_WAKEUP || 
                phase == EVENING_TRANSITION) {
                
                vpd_active = true;
                float current_vpd = calculate_current_vpd(in_temp, in_hum);

                if (current_vpd < target_vpd_min) {
                    vpd_f = constrain((target_vpd_min - current_vpd) / 0.3f, 0.0f, 1.0f);
                } else if (current_vpd > target_vpd_max) {
                    vpd_f = constrain((current_vpd - target_vpd_max) / 0.5f, 0.0f, 1.0f);
                }
            }

            // Dominanter Faktor
            mix_factor = max({t_f, h_f, vpd_f});

            // === Phasen-Anpassung ===
            if (phase == NIGHT_RECOVERY) {
                mix_factor *= 0.5f;           // Nachtreduktion (nur Temp + Hum)
                exhaust_fan_state_reason = "night_auto";
            } 
            else if (phase == EVENING_TRANSITION) {
                mix_factor *= 0.75f;
                exhaust_fan_state_reason = vpd_active && vpd_f > 0.1f ? "vpd_sunset" : "sunset_ramp";
            } 
            else if (phase == MORNING_WAKEUP) {
                mix_factor *= 1.1f;
                exhaust_fan_state_reason = vpd_active && vpd_f > 0.1f ? "vpd_sunrise" : "sunrise_ramp";
            } 
            else { // DAY_TRANSPIRE
                exhaust_fan_state_reason = (vpd_f > 0.15f) ? "vpd_day" : 
                                          (t_f > h_f ? "temp_day" : "hum_day");
            }

            int fan_range = exhaust_fan_pct - exhaust_fan_min;
            final_pct = (float)exhaust_fan_min + (fan_range * mix_factor);
        } 
        else {
            // Sensor-Failsafe
            final_pct = (float)exhaust_fan_pct;
            exhaust_fan_state_reason = "CRIT_SENSOR_TIMEOUT";
        }

        // ============================================================
        // 4. SMART FAILSAFE ( unverändert )
        // ============================================================
        if (sensors_valid) {
            bool values_too_high = (in_temp > target_temp_max || in_hum > target_humidity_max);
            bool outside_is_bad = (out_temp > in_temp + 0.2f || out_hum > in_hum + 2.0f);

            if (out_ok && values_too_high && outside_is_bad && !air_can_be_refined) {
                failsafe_phase += 1;
                float pulse = (sin(failsafe_phase * 0.15f) * 0.5f + 0.5f);
                int fs_min = max((int)EXHAUST_FAILSAFE_MIN, exhaust_fan_min);
                final_pct = fs_min + ((exhaust_fan_pct - fs_min) * pulse);
                exhaust_fan_state_reason = "failsafe_unrefinable";
            } 
            else if (values_too_high && air_can_be_refined) {
                exhaust_fan_state_reason = "using_refined_air";
            }
        }
    }

    // ============================================================
    // 5. CHAOS & HARDWARE OUTPUT
    // ============================================================
    if (exhaust_fan_chaos_active) {
        float wobble = (float)random(-80, 81) / 10.0f; // +/- 8%
        final_pct += wobble;
        if (!is_manual && exhaust_fan_state_reason.startsWith("day")) {
            exhaust_fan_state_reason = "chaos_active";
        }
    }

    // Finale Begrenzung auf User-Settings
    final_pct = constrain(final_pct, (float)exhaust_fan_min, (float)exhaust_fan_pct);
    current_exhaust_fan_speed = (int)(final_pct + 0.5f);
    
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
            
                if (m == "auto") {
                    current_exhaust_fan_mode = exhaust_fan_MODE_AUTOMATIC;
                } else if (m == "man") {
                    current_exhaust_fan_mode = exhaust_fan_MODE_MANUAL;
                }
            
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
    doc["exhaust_fan_mode"] =
        (current_exhaust_fan_mode == exhaust_fan_MODE_AUTOMATIC)
        ? "auto"
        : "man";
    doc["target_temp_min"] = target_temp_min;
    doc["target_temp_max"] = target_temp_max;
    doc["target_humidity_min"] = target_humidity_min;
    doc["target_humidity_max"] = target_humidity_max;
    doc["target_vpd_min"] = target_vpd_min;
    doc["target_vpd_max"] = target_vpd_max;
    
    doc["rev_exhaust"] = exhaust_fan_rev;        // ← WICHTIG: Eigenes Rev zurücksenden
    doc["rev_init_exhaust"] = exhaust_fan_init_rev;
    doc["plant_phase"] = (int)current_phase;
    doc["exhaust_fan_chaos_active"] = exhaust_fan_chaos_active;
    doc["exhaust_fan_state_reason"] = exhaust_fan_state_reason;
}