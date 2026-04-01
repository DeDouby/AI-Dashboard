#include "fan.h"
#include <Preferences.h> // NEU: Für persistente Speicherung
// Variablen mit sicheren Startwerten
static uint8_t _fan_pin = 4;
static uint8_t _tacho_pin = 7; 
Preferences fanPrefs;
int current_fan_speed = 60;
FanMode current_fan_mode = FAN_MODE_NATURAL; // Direkt mit Natural starten
int current_fan_min_speed = 20; // Standardmäßig 20% Min-Speed
volatile int pulse_count = 0; 
static uint32_t last_rpm_check = 0;
static int current_rpm = 0;
// Zeitstempel für Entprellung
static uint32_t last_pulse_time = 0;



// Hilfsfunktion: Speichern
void fan_save_state() {
    fanPrefs.putInt("speed", current_fan_speed);
    fanPrefs.putInt("mode", (int)current_fan_mode);
    fanPrefs.putInt("min_speed", current_fan_min_speed);
}

void IRAM_ATTR count_pulse() {
    uint32_t now = micros();
    if (now - last_pulse_time > 2000) { 
        pulse_count++;
        last_pulse_time = now;
    }
}

void fan_init(uint8_t pin, uint8_t tacho_pin) {
    _fan_pin = pin;
    _tacho_pin = tacho_pin;
    
    // 1. PWM Setup
    ledcAttach(_fan_pin, 25000, 8); 
    
    // 2. Preferences laden (Namespace "fan")
    fanPrefs.begin("fan", false);
    current_fan_speed = fanPrefs.getInt("speed", 60);       // Default 60
    current_fan_mode = (FanMode)fanPrefs.getInt("mode", 1); // 1 = FAN_MODE_NATURAL
    current_fan_min_speed = fanPrefs.getInt("min_speed", 20); // Default 20
    
    // 3. Tacho Setup
    if (_tacho_pin != 255) {
        pinMode(_tacho_pin, INPUT_PULLUP);
        delay(50); 
        int irq = digitalPinToInterrupt(_tacho_pin);
        if (irq != -1) {
            attachInterrupt(irq, count_pulse, FALLING);
        }
    }

    // Initialen Speed setzen (entweder Default oder geladener Wert)
    fan_set_speed(current_fan_speed);
}

void fan_set_speed(int percent) {
    current_fan_speed = constrain(percent, 0, 100);
    
    // Speichern, damit es nach Reboot bleibt
    fan_save_state();

    if(current_fan_mode == FAN_MODE_MANUAL) {
        uint32_t duty = 0;
        if (current_fan_speed > 0) {
            duty = map(current_fan_speed, 1, 100, 65, 255);
        }
        ledcWrite(_fan_pin, duty);
    }
}

void fan_set_mode(FanMode mode) {
    current_fan_mode = mode;
    fan_save_state(); // Modus speichern
}

// NEU: Damit du auch den Min-Speed von extern (Web/UI) setzen kannst
void fan_set_min_speed(int percent) {
    current_fan_min_speed = constrain(percent, 0, 100);
    fan_save_state();
}




int fan_get_rpm() {
    uint32_t now = millis();
    if (now - last_rpm_check >= 1000) {

        noInterrupts();
        uint32_t pulses = pulse_count;
        pulse_count = 0;
        interrupts();

        current_rpm = (pulses * 60) / 2;
        last_rpm_check = now;
    }
    return current_rpm;
}

void fan_update() {
    if (current_fan_mode == FAN_MODE_MANUAL) return;

    static uint32_t last_wind_change = 0;
    if (millis() - last_wind_change > 1500) {
        float mix_factor = 0;

        if (current_fan_mode == FAN_MODE_NATURAL) {
            // Schwingt sauber zwischen 0.0 und 1.0
            mix_factor = 0.5 + (sin(millis() / 3000.0) * 0.5);
        } 
        else if (current_fan_mode == FAN_MODE_CHAOTIC) {
            mix_factor = random(0, 101) / 100.0;
        }

        // DER CLOU: Wir skalieren den Mix-Faktor auf den Bereich zwischen MIN und MAX
        // Formel: Min + (Differenz * Mix)
        int diff = current_fan_speed - current_fan_min_speed;
        if (diff < 0) diff = 0; // Sicherheitshalber

        int dynamic_speed = current_fan_min_speed + (int)(diff * mix_factor);
        
        // PWM Mapping (unser Mars Gaming Schutz bleibt!)
        uint32_t duty = 0;
        if (dynamic_speed > 0) {
            duty = map(dynamic_speed, 1, 100, 65, 255);
        }
        
        ledcWrite(_fan_pin, duty);
        last_wind_change = millis();
    }

}