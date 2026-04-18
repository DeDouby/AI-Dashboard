#include "power_manager.h"

#define BAT_PIN 12

void power_manager_init()
{
    pinMode(BAT_PIN, INPUT);
}

// --- BATTERY VOLTAGE (BLE / WEB / LOGIC) ---
float get_battery_voltage_now()
{
    uint16_t analogVolts = analogReadMilliVolts(BAT_PIN);
    return (analogVolts * 3.0f) / 1000.0f;
}

// --- OPTIONAL: PERIODIC POWER MGMT ---
void power_manager_update()
{
    // Headless: aktuell keine dynamische CPU / Sleep Logik
    // Kann später für Low-Power erweitert werden
}