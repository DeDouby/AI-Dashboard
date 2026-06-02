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

#include "circulation_fan.h"
#include <Preferences.h> // NEU: Für persistente Speicherung
#include "config.h"
#define CIRC_FAN_PULSES_PER_REV 2
#define CIRC_FAN_DEBOUNCE_US 500
// Variablen mit sicheren Startwerten
static uint8_t _circulation_fan_pin; // Keine Zahl hier!
static uint8_t _tacho_pin;          // Keine Zahl hier!
Preferences circulation_fanPrefs;
int current_circulation_fan_speed = 60;
circulation_fanMode current_circulation_fan_mode = circulation_fan_MODE_NATURAL; // Direkt mit Natural starten
int current_circulation_fan_min_speed = 20; // Standardmäßig 20% Min-Speed
int effective_circulation_fan_speed = 0;    // Das ist das SPEED_NOW (Ist)
volatile uint32_t circulation_fan_pulse_count = 0;
static uint32_t last_circulation_fan_rpm_check = 0;
static int current_circulation_fan_rpm = 0;
// Zeitstempel für Entprellung
static uint32_t last_circulation_fan_pulse_time = 0;
static uint32_t circulation_fan_rev = 0;     // ← NEU: Eigenes Revision für dieses Modul
static uint32_t circulation_fan_init_rev = 0;

// Hilfsfunktion: Speichern
void circulation_fan_save_state() {
    circulation_fanPrefs.putInt("speed", current_circulation_fan_speed);
    circulation_fanPrefs.putInt("mode", (int)current_circulation_fan_mode);
    circulation_fanPrefs.putInt("min_speed", current_circulation_fan_min_speed);
}

void IRAM_ATTR count_circ_fan_pulse() {
    uint32_t now = micros();
    // Nutze den korrekten Namen: last_circulation_fan_pulse_time
    if (now - last_circulation_fan_pulse_time > 800) { 
        circulation_fan_pulse_count++;
        last_circulation_fan_pulse_time = now;
    }
}

void circulation_fan_init(uint8_t pin, uint8_t tacho_pin) {
    _circulation_fan_pin = pin;
    _tacho_pin = tacho_pin;
    
    ledcAttach(_circulation_fan_pin, 25000, 8); 
    
    circulation_fanPrefs.begin("circulation_fan", false);
    current_circulation_fan_speed = circulation_fanPrefs.getInt("speed", 60);
    // WICHTIG: Fallback auf 1 (NATURAL), falls nichts gespeichert ist
    current_circulation_fan_mode = (circulation_fanMode)circulation_fanPrefs.getInt("mode", 1); 
    current_circulation_fan_min_speed = circulation_fanPrefs.getInt("min_speed", 20);
    
    // 3. Tacho Setup
    if (tacho_pin != 255) {
            pinMode(tacho_pin, INPUT_PULLUP);
            int irq = digitalPinToInterrupt(tacho_pin);
            // Hier muss der Name der Funktion oben stehen: count_circ_fan_pulse
            attachInterrupt(irq, count_circ_fan_pulse, FALLING); 
        }
    

    // INITIALER SETTER FIX:
    // Wir rufen circulation_fan_set_mode auf, damit die Logik sofort greift
    circulation_fan_init_rev = millis() + 1;
    circulation_fan_rev = millis();
    circulation_fan_set_mode(current_circulation_fan_mode);
    circulation_fan_set_speed(current_circulation_fan_speed);

}

void circulation_fan_set_speed(int percent) {
    current_circulation_fan_speed = constrain(percent, 0, 100);
    
    // Speichern, damit es nach Reboot bleibt
    circulation_fan_save_state();

    if(current_circulation_fan_mode == circulation_fan_MODE_MANUAL) {
        uint32_t duty = 0;
        if (current_circulation_fan_speed > 0) {
            duty = map(current_circulation_fan_speed, 1, 100, 65, 255);
        }
        ledcWrite(_circulation_fan_pin, duty);
    }
}

void circulation_fan_set_mode(circulation_fanMode mode) {
    current_circulation_fan_mode = mode;
    circulation_fan_save_state(); // Modus speichern
}

// NEU: Damit du auch den Min-Speed von extern (Web/UI) setzen kannst
void circulation_fan_set_min_speed(int percent) {
    current_circulation_fan_min_speed = constrain(percent, 0, 100);
    circulation_fan_save_state();
}




// 3. Die RPM-Abfrage (Reaktionsfreudige Glättung)
int circulation_fan_get_rpm() {
    uint32_t now = millis();
    // Nutze den korrekten Namen: last_circulation_fan_rpm_check
    if (now - last_circulation_fan_rpm_check >= 1000) {
        noInterrupts();
        uint32_t pulses = circulation_fan_pulse_count;
        circulation_fan_pulse_count = 0;
        interrupts();

        // 2 Pulse pro Umdrehung
        int new_rpm = (pulses * 60) / 2; 

        // Schnelle Glättung (60% neu, 40% alt)
        if (current_circulation_fan_rpm == 0) {
            current_circulation_fan_rpm = new_rpm;
        } else {
            current_circulation_fan_rpm = (current_circulation_fan_rpm * 0.4f) + (new_rpm * 0.6f);
        }
        
        last_circulation_fan_rpm_check = now;
    }
    return current_circulation_fan_rpm;
}

void circulation_fan_update() {
    // Falls Manuell: Der effektive Wert ist einfach das Target
    if (current_circulation_fan_mode == circulation_fan_MODE_MANUAL) {
    
        effective_circulation_fan_speed = current_circulation_fan_speed;
    
        uint32_t duty = 0;
    
        if (effective_circulation_fan_speed > 0) {
            duty = map(
                effective_circulation_fan_speed,
                1,
                100,
                65,
                255
            );
        }
    
        ledcWrite(_circulation_fan_pin, duty);
    
        return;
    }

    static uint32_t last_wind_change = 0;
    if (millis() - last_wind_change > 1500) {
        float mix_factor = 0;

        if (current_circulation_fan_mode == circulation_fan_MODE_NATURAL) {
            mix_factor = 0.5 + (sin(millis() / 3000.0) * 0.5);
        } 
        else if (current_circulation_fan_mode == circulation_fan_MODE_CHAOTIC) {
            mix_factor = random(0, 101) / 100.0;
        }

        int diff = current_circulation_fan_speed - current_circulation_fan_min_speed;
        if (diff < 0) diff = 0; 

        // Berechnung des aktuellen IST-Wertes
        effective_circulation_fan_speed = current_circulation_fan_min_speed + (int)(diff * mix_factor);
        
        // PWM Mapping
        uint32_t duty = 0;
        if (effective_circulation_fan_speed > 0) {
            duty = map(effective_circulation_fan_speed, 1, 100, 65, 255);
        }
        
        ledcWrite(_circulation_fan_pin, duty);
        last_wind_change = millis();
    }
}

void circulation_fan_process_json(JsonObject doc) {
    bool flash_changed = false;

    // 1. Handshake (RAM only)
    if (doc.containsKey("rev_init_circfan")) {
        circulation_fan_init_rev = doc["rev_init_circfan"];
        // Kein flash_changed!
    }

    // 2. Daten-Revision (Flash relevant)
    if (doc.containsKey("rev_circfan")) {
        uint32_t received_rev = doc["rev_circfan"];
        if (received_rev > circulation_fan_rev) {
            circulation_fan_rev = received_rev;

            if (doc.containsKey("circulation_fan_pct")) {
                current_circulation_fan_speed = constrain((int)doc["circulation_fan_pct"], 0, 100);
                flash_changed = true;
            }
            if (doc.containsKey("circulation_fan_min")) {
                current_circulation_fan_min_speed = constrain((int)doc["circulation_fan_min"], 0, 100);
                flash_changed = true;
            }
            if (doc.containsKey("circulation_fan_mode")) {
                String m = doc["circulation_fan_mode"];
                if (m == "nat") current_circulation_fan_mode = circulation_fan_MODE_NATURAL;
                else if (m == "chao") current_circulation_fan_mode = circulation_fan_MODE_CHAOTIC;
                else current_circulation_fan_mode = circulation_fan_MODE_MANUAL;
                flash_changed = true;
            }
        }
    }

    if (flash_changed) {
        // Logik anwenden & persistieren
        if (current_circulation_fan_mode == circulation_fan_MODE_MANUAL) {
            circulation_fan_set_speed(current_circulation_fan_speed);
        }
        circulation_fan_save_state();
    }
}

void circulation_fan_get_status(JsonObject doc) {
    doc["circulation_fan_rpm"] = circulation_fan_get_rpm();
    doc["circulation_fan_pct"] = current_circulation_fan_speed;
    doc["circulation_fan_speed_now"] = effective_circulation_fan_speed;
    doc["circulation_fan_min"] = current_circulation_fan_min_speed;
    doc["circulation_fan_mode"] = (current_circulation_fan_mode == circulation_fan_MODE_NATURAL) ? "nat" : 
                                 (current_circulation_fan_mode == circulation_fan_MODE_CHAOTIC) ? "chao" : "manual";
    
    doc["rev_circfan"] = circulation_fan_rev;        // ← WICHTIG: Eigenes Rev zurücksenden
    doc["rev_init_circfan"] = circulation_fan_init_rev;
}