#include "fan.h"

// Variablen mit sicheren Startwerten
static uint8_t _fan_pin = 4;
static uint8_t _tacho_pin = 7; 

int current_fan_speed = 60;
FanMode current_fan_mode = FAN_MODE_NATURAL; // Direkt mit Natural starten

volatile int pulse_count = 0; 
static uint32_t last_rpm_check = 0;
static int current_rpm = 0;
// Zeitstempel für Entprellung
static uint32_t last_pulse_time = 0;

void IRAM_ATTR count_pulse() {
    uint32_t now = micros(); // Mikrosekunden für höhere Präzision
    // Ein Lüfter bei 5000 RPM liefert ca. 166 Impulse/Sek (bei 2 Pulsen pro Umdrehung)
    // Das entspricht ca. 6000 Mikrosekunden pro Puls.
    // Wir ignorieren alles, was schneller als 2000 Mikrosekunden (30000 RPM) kommt.
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
    
    // 2. Tacho Setup mit Sicherheits-Check
    if (_tacho_pin != 255) { // 255 = Deaktiviert
        pinMode(_tacho_pin, INPUT_PULLUP);
        
        // KURZE PAUSE: Damit der Pullup-Widerstand stabil auf 3.3V ziehen kann
        delay(50); 
        
        int irq = digitalPinToInterrupt(_tacho_pin);
        if (irq != -1) {
            attachInterrupt(irq, count_pulse, FALLING);
     
        }
    fan_set_speed(current_fan_speed);
    }

}

void fan_set_speed(int percent) {
    current_fan_speed = constrain(percent, 0, 100);
    if(current_fan_mode == FAN_MODE_MANUAL) {
        uint32_t duty = 0;
        if (current_fan_speed > 0) {
            // Mars Gaming Mapping (25% bis 100%)
            duty = map(current_fan_speed, 1, 100, 65, 255);
        }
        ledcWrite(_fan_pin, duty);
    }
}

void fan_set_mode(FanMode mode) {
    current_fan_mode = mode;
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
    // Im manuellen Modus macht die Loop nichts, da fan_set_speed direkt schreibt
    if (current_fan_mode == FAN_MODE_MANUAL) return;

    static uint32_t last_wind_change = 0;
    // Alle 1,5 Sekunden berechnen wir die "Mischung" neu
    if (millis() - last_wind_change > 1500) {
        float mix_factor = 0;

        if (current_fan_mode == FAN_MODE_NATURAL) {
            // Sinus-Welle zwischen 0.4 und 1.0
            mix_factor = 0.7 + (sin(millis() / 3000.0) * 0.3);
        } 
        else if (current_fan_mode == FAN_MODE_CHAOTIC) {
            // Zufallswert zwischen 0.3 und 1.0
            mix_factor = random(30, 101) / 100.0;
        }

        // Jetzt kommt der Clou: Wir multiplizieren den Slider-Wert mit dem Mix-Faktor
        // Beispiel: Slider 60% * Mix 0.5 = 30% Power
        int dynamic_speed = (int)(current_fan_speed * mix_factor);
        
        // Mars Gaming Mindestdrehzahl-Schutz (65-255 PWM)
        uint32_t duty = 0;
        if (dynamic_speed > 0) {
            duty = map(dynamic_speed, 1, 100, 65, 255);
        }
        
        ledcWrite(_fan_pin, duty);
        last_wind_change = millis();
    }
}