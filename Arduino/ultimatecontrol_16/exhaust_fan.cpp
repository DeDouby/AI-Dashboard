#include "exhaust_fan.h"
#include <Preferences.h> // NEU: Für persistente Speicherung
// Variablen mit sicheren Startwerten
static uint8_t _exhaust_fan_pin;
static uint8_t _tacho_pin; 
Preferences exhaust_fanPrefs;
int current_exhaust_fan_speed = 60;
exhaust_fanMode current_exhaust_fan_mode = exhaust_fan_MODE_AUTOMATIC; // Direkt mit AUTOMATIC starten
int current_exhaust_fan_min_speed = 20; // Standardmäßig 20% Min-Speed
volatile int exhaust_fan_pulse_count = 0; 
static uint32_t last_exhaust_fan_rpm_check = 0;
static int current_exhaust_fan_rpm = 0;
// Zeitstempel für Entprellung
static uint32_t last_exhaust_fan_pulse_time = 0;



// Hilfsfunktion: Speichern
void exhaust_fan_save_state() {
    exhaust_fanPrefs.putInt("speed", current_exhaust_fan_speed);
    exhaust_fanPrefs.putInt("mode", (int)current_exhaust_fan_mode);
    exhaust_fanPrefs.putInt("min_speed", current_exhaust_fan_min_speed);
}

void IRAM_ATTR count_exhaust_fan_pulse() {
    uint32_t now = micros();
    if (now - last_exhaust_fan_pulse_time > 2000) { 
        exhaust_fan_pulse_count++;
        last_exhaust_fan_pulse_time = now;
    }
}

void exhaust_fan_init(uint8_t pin, uint8_t tacho_pin) {
    _exhaust_fan_pin = pin;
    _tacho_pin = tacho_pin;
    
    ledcAttach(_exhaust_fan_pin, 25000, 8); 
    
    exhaust_fanPrefs.begin("exhaust_fan", false);
    current_exhaust_fan_speed = exhaust_fanPrefs.getInt("speed", 60);
    // WICHTIG: Fallback auf 1 (AUTOMATIC), falls nichts gespeichert ist
    current_exhaust_fan_mode = (exhaust_fanMode)exhaust_fanPrefs.getInt("mode", 1); 
    current_exhaust_fan_min_speed = exhaust_fanPrefs.getInt("min_speed", 20);
    
    // 3. Tacho Setup
    if (_tacho_pin != 255) {
        pinMode(_tacho_pin, INPUT_PULLUP);
        delay(50); 
        int irq = digitalPinToInterrupt(_tacho_pin);
        if (irq != -1) {
            attachInterrupt(irq, count_exhaust_fan_pulse, FALLING);
        }
    }

    // INITIALER SETTER FIX:
    // Wir rufen exhaust_fan_set_mode auf, damit die Logik sofort greift
    exhaust_fan_set_mode(current_exhaust_fan_mode);
    exhaust_fan_set_speed(current_exhaust_fan_speed);
}

void exhaust_fan_set_speed(int percent) {
    current_exhaust_fan_speed = constrain(percent, 0, 100);
    
    // Speichern, damit es nach Reboot bleibt
    exhaust_fan_save_state();

    if(current_exhaust_fan_mode == exhaust_fan_MODE_MANUAL) {
        uint32_t duty = 0;
        if (current_exhaust_fan_speed > 0) {
            duty = map(current_exhaust_fan_speed, 1, 100, 65, 255);
        }
        ledcWrite(_exhaust_fan_pin, duty);
    }
}

void exhaust_fan_set_mode(exhaust_fanMode mode) {
    current_exhaust_fan_mode = mode;
    exhaust_fan_save_state(); // Modus speichern
}

// NEU: Damit du auch den Min-Speed von extern (Web/UI) setzen kannst
void exhaust_fan_set_min_speed(int percent) {
    current_exhaust_fan_min_speed = constrain(percent, 0, 100);
    exhaust_fan_save_state();
}




int exhaust_fan_get_rpm() {
    uint32_t now = millis();
    if (now - last_exhaust_fan_rpm_check >= 1000) {

        noInterrupts();
        uint32_t exhaust_fan_pulses = exhaust_fan_pulse_count;
        exhaust_fan_pulse_count = 0;
        interrupts();

        current_exhaust_fan_rpm = (exhaust_fan_pulses * 60) / 2;
        last_exhaust_fan_rpm_check = now;
    }
    return current_exhaust_fan_rpm;
}

void exhaust_fan_update() {
    if (current_exhaust_fan_mode == exhaust_fan_MODE_MANUAL) return;

    static uint32_t last_wind_change = 0;
    if (millis() - last_wind_change > 1500) {
        float mix_factor = 0;

        if (current_exhaust_fan_mode == exhaust_fan_MODE_AUTOMATIC) {
            // Schwingt sauber zwischen 0.0 und 1.0
            mix_factor = 0.5 + (sin(millis() / 3000.0) * 0.5);
        } 
        else if (current_exhaust_fan_mode == exhaust_fan_MODE_CHAOTIC) {
            mix_factor = random(0, 101) / 100.0;
        }

        // DER CLOU: Wir skalieren den Mix-Faktor auf den Bereich zwischen MIN und MAX
        // Formel: Min + (Differenz * Mix)
        int diff = current_exhaust_fan_speed - current_exhaust_fan_min_speed;
        if (diff < 0) diff = 0; // Sicherheitshalber

        int dynamic_speed = current_exhaust_fan_min_speed + (int)(diff * mix_factor);
        
        // PWM Mapping (unser Mars Gaming Schutz bleibt!)
        uint32_t duty = 0;
        if (dynamic_speed > 0) {
            duty = map(dynamic_speed, 1, 100, 65, 255);
        }
        
        ledcWrite(_exhaust_fan_pin, duty);
        last_wind_change = millis();
    }

}