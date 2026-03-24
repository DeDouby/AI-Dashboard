#include "power_manager.h"
#include "display_config.h"
#include "ui_helper.h"

#define BAT_PIN 12
#define LEDC_FREQ 5000
#define LEDC_TIMER_10_BIT 10
#define GFX_BL 46

void power_manager_init()
{
    pinMode(BAT_PIN, INPUT);
}
// Füge dies am Ende von power_manager.cpp hinzu:
float get_battery_voltage_now() {
    uint16_t analogVolts = analogReadMilliVolts(BAT_PIN);
    return (analogVolts * 3.0) / 1000.0; // Die gleiche Rechnung wie in update_battery_ui
}

void update_battery_ui()
{
    uint16_t analogVolts = analogReadMilliVolts(BAT_PIN);
    float voltage = (analogVolts * 3.0) / 1000.0;

    char volt_str[10];
    dtostrf(voltage, 4, 2, volt_str);

    const char *bat_icon;

    if (voltage > 4.0)
        bat_icon = LV_SYMBOL_BATTERY_FULL;
    else if (voltage > 3.7)
        bat_icon = LV_SYMBOL_BATTERY_3;
    else if (voltage > 3.4)
        bat_icon = LV_SYMBOL_BATTERY_1;
    else
        bat_icon = LV_SYMBOL_BATTERY_EMPTY;

    lv_label_set_text_fmt(ui_battery_label, "%s %s V", bat_icon, volt_str);
}

void power_manager_update()
{
    uint32_t last_interaction = lv_disp_get_inactive_time(NULL);

    // --- GEHE IN DEN SCHLAF (80 MHz) ---
    if (last_interaction > screen_timeout && !is_display_off)
    {
        Serial.println(">>> System Sleep: Scaling down to 80MHz...");
        Serial.flush(); 

        ledcWrite(GFX_BL, 0); // Backlight aus
        gfx->displayOff();
        is_display_off = true;

        setCpuFrequencyMhz(160); // Sicherer Hafen für BLE
        
        delay(20); // Puffer für Hardware-Umschaltung
        Serial.print("Confirmed Frequency: ");
        Serial.print(getCpuFrequencyMhz());
        Serial.println(" MHz");
    }
    // --- AUFWACHEN (240 MHz) ---
    else if (last_interaction < screen_timeout && is_display_off)
    {
        Serial.println(">>> System Wakeup: Boosting to 240MHz...");
        Serial.flush();

        setCpuFrequencyMhz(240);
        
        delay(20); 
        gfx->displayOn();

        // Brightness wiederherstellen
        uint32_t duty = (1023 * global_brightness_percent) / 100;
        ledcWrite(GFX_BL, duty);

        is_display_off = false;
        
        Serial.print("Confirmed Frequency: ");
        Serial.print(getCpuFrequencyMhz());
        Serial.println(" MHz");
    }
}