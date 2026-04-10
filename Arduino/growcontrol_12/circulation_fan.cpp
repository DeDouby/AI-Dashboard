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


#include "circulation_fan.h"
#include <Preferences.h> // NEU: Für persistente Speicherung
#include "config.h"

// Variablen mit sicheren Startwerten
static uint8_t _circulation_fan_pin; // Keine Zahl hier!
static uint8_t _tacho_pin;          // Keine Zahl hier!
Preferences circulation_fanPrefs;
int current_circulation_fan_speed = 60;
circulation_fanMode current_circulation_fan_mode = circulation_fan_MODE_NATURAL; // Direkt mit Natural starten
int current_circulation_fan_min_speed = 20; // Standardmäßig 20% Min-Speed
int effective_circulation_fan_speed = 0;    // Das ist das SPEED_NOW (Ist)
volatile int circulation_fan_pulse_count = 0; 
static uint32_t last_circulation_fan_rpm_check = 0;
static int current_circulation_fan_rpm = 0;
// Zeitstempel für Entprellung
static uint32_t last_circulation_fan_pulse_time = 0;



// Hilfsfunktion: Speichern
void circulation_fan_save_state() {
    circulation_fanPrefs.putInt("speed", current_circulation_fan_speed);
    circulation_fanPrefs.putInt("mode", (int)current_circulation_fan_mode);
    circulation_fanPrefs.putInt("min_speed", current_circulation_fan_min_speed);
}

void IRAM_ATTR count_circulation_fan_pulse() {
    uint32_t now = micros();
    if (now - last_circulation_fan_pulse_time > 2000) { 
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
    if (_tacho_pin != 255) {
        pinMode(_tacho_pin, INPUT_PULLUP);
        delay(50); 
        int irq = digitalPinToInterrupt(_tacho_pin);
        if (irq != -1) {
            attachInterrupt(irq, count_circulation_fan_pulse, FALLING);
        }
    }

    // INITIALER SETTER FIX:
    // Wir rufen circulation_fan_set_mode auf, damit die Logik sofort greift
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




int circulation_fan_get_rpm() {
    uint32_t now = millis();
    if (now - last_circulation_fan_rpm_check >= 1000) {

        noInterrupts();
        uint32_t circulation_fan_pulses = circulation_fan_pulse_count;
        circulation_fan_pulse_count = 0;
        interrupts();

        current_circulation_fan_rpm = (circulation_fan_pulses * 60) / 2;
        last_circulation_fan_rpm_check = now;
    }
    return current_circulation_fan_rpm;
}

void circulation_fan_update() {
    // Falls Manuell: Der effektive Wert ist einfach das Target
    if (current_circulation_fan_mode == circulation_fan_MODE_MANUAL) {
        effective_circulation_fan_speed = current_circulation_fan_speed;
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
    bool changed = false;

    // 1. Geschwindigkeit (Max)
    if (doc.containsKey("circulation_fan_pct")) {
        current_circulation_fan_speed = constrain((int)doc["circulation_fan_pct"], 0, 100);
        changed = true;
    }

    // 2. Minimum Geschwindigkeit (Boden)
    if (doc.containsKey("circulation_fan_min")) {
        current_circulation_fan_min_speed = constrain((int)doc["circulation_fan_min"], 0, 100);
        changed = true;
    }

    // 3. Modus (man, nat, chao)
    if (doc.containsKey("circulation_fan_mode")) {
        String m = doc["circulation_fan_mode"];
        if (m == "nat") current_circulation_fan_mode = circulation_fan_MODE_NATURAL;
        else if (m == "chao") current_circulation_fan_mode = circulation_fan_MODE_CHAOTIC;
        else current_circulation_fan_mode = circulation_fan_MODE_MANUAL;
        changed = true;
    }

    // Wenn sich was geändert hat: Sofort Update und Speichern
    if (changed) {
        // Falls Manuell: Speed sofort anwenden
        if (current_circulation_fan_mode == circulation_fan_MODE_MANUAL) {
            circulation_fan_set_speed(current_circulation_fan_speed);
        }
        circulation_fan_save_state();
        Serial.println("Circulation Fan Settings updated.");
    }
}
void circulation_fan_get_status(JsonObject doc) {
    doc["circulation_fan_rpm"] = circulation_fan_get_rpm();
    doc["circulation_fan_pct"] = current_circulation_fan_speed;
    doc["circulation_fan_speed_now"] = effective_circulation_fan_speed; // Realer Speed (Anzeige)
    doc["circulation_fan_min"] = current_circulation_fan_min_speed;
    doc["circulation_fan_mode"] = (current_circulation_fan_mode == circulation_fan_MODE_NATURAL) ? "nat" : 
                                 (current_circulation_fan_mode == circulation_fan_MODE_CHAOTIC) ? "chao" : "man";
}