#include "display_config.h"
#include "power_manager.h"
#include "sensor.h"
#include "ble_bridge.h"
#include "ui_helper.h"
#include "logic_helper.h"
#include "hardware_init.h"
#include "circulation_fan.h" 
#include "exhaust_fan.h" 
#include "config.h"
#include "web_server.h" // Modul einbinden
#include "light_control.h"
// BLE & System
BLEBridge bleBridge;
uint32_t screen_timeout = 30000; 
bool is_display_off = false;

// WLAN Daten (Wichtig: bleiben hier, damit du sie schnell ändern kannst)
const char* my_ssid = "Cudy-Indoor"; 
const char* my_password = "Hackintosh!";

// DIE EINZIGE DEFINITION DES SERVERS
WebServer server(80); 
// Hardware & Sensoren (MÜSSEN hier bleiben für die anderen .cpp Dateien!)
TwoWire I2C_Sensor = TwoWire(1);               
Adafruit_SHT31 sht31 = Adafruit_SHT31(&I2C_Sensor); 
bool externalSensorFound = false;
int global_brightness_percent = 80;
int current_rev = 0; // Die aktuelle Revisionsnummer auf dem Gerät


// --- HILFSFUNKTION FÜR DIE UHRZEIT ---
String get_current_time_str() {
    struct tm timeinfo;
    if (!getLocalTime(&timeinfo)) {
        return "--:--"; // Zeigt das an, wenn noch kein WLAN/Sync da ist
    }
    char timeStr[10];
    // Format: HH:MM (z.B. 14:30)
    strftime(timeStr, sizeof(timeStr), "%H:%M", &timeinfo);
    return String(timeStr);
}
void setup() {
    setCpuFrequencyMhz(240);
    Serial.begin(115200);

    init_hardware();
    power_manager_init();
    circulation_fan_init(PIN_CIRC_FAN, PIN_CIRC_TACHO);
    exhaust_fan_init(PIN_EXH_FAN, PIN_EXH_TACHO);
    light_init();
    externalSensorFound = initExternalSensor();

    setup_lvgl();
    setup_ui();

    // WEB-MODUL STARTEN
    WebModule::init(my_ssid, my_password);

    bleBridge.begin();
    Serial.println("System bereit.");
}

// ---------- LOOP ----------
void loop() {
    // WEB-CLIENTS BEDIENEN
    WebModule::update();

    lv_timer_handler();
    circulation_fan_update(); 
    exhaust_fan_update(); 

    light_update();

    power_manager_update();

    static uint32_t last_update = 0;
    static uint32_t last_ble_update = 0;

    if (millis() - last_update > 500) {
        last_update = millis();
        char buf[32];          
        char v_buf_int[32];    
        
        float temp_in  = getTempIn();     
        float temp_ext = getTempExt();         
        float humid_ext = getExternalHumidity(); 
    
        float logic_temp_ext = (temp_ext <= -0.4f) ? temp_in : temp_ext;
        float logic_humid_ext = (humid_ext <= -0.4f) ? 0.0f : humid_ext;
        update_sensor_logic(logic_temp_ext, temp_in, logic_humid_ext);

        // --- 3. UI UPDATES: MAIN TILE (Interne Sensoren) ---
        if (temp_in > -250.0f) {
            // Interner Sensor ist DA
            dtostrf(temp_in, 4, 2, buf);
            if(ui_temp_label) lv_label_set_text_fmt(ui_temp_label, "%s °C", buf);
            
            dtostrf(currentVPDIn, 4, 2, v_buf_int);
            if(ui_main_vpd_label) lv_label_set_text_fmt(ui_main_vpd_label, "%s kPa", v_buf_int);
            if(ui_vpd_int_screen_label) lv_label_set_text(ui_vpd_int_screen_label, v_buf_int);
        } 
        else {
            // Interner NTC ABGEZOGEN (Pseudo-Wert -256 erkannt)
            if(ui_temp_label) lv_label_set_text(ui_temp_label, "--.- °C");
            if(ui_main_vpd_label) lv_label_set_text(ui_main_vpd_label, "-.-- kPa");
            if(ui_vpd_int_screen_label) lv_label_set_text(ui_vpd_int_screen_label, "-.--");
        }


        // --- 4. UI UPDATES: EXTERNAL & VPD SCREEN ---
        if (temp_ext > -250.0f && humid_ext > -250.0f) {
            // SENSOR IST DA -> Werte anzeigen
            char b_t[16], b_h[16], b_v_ext[16], b_v_leaf[16];
            dtostrf(temp_ext, 4, 2, b_t);       // 1 Nachkommastelle für Sauberkeit
            dtostrf(humid_ext, 4, 2, b_h);
            dtostrf(currentVPD, 4, 2, b_v_ext);    
            dtostrf(currentVPDLeaf, 4, 2, b_v_leaf); 

            if(ui_chart_temp_label) lv_label_set_text_fmt(ui_chart_temp_label, "%s °C", b_t);
            if(ui_humid_label)      lv_label_set_text_fmt(ui_humid_label, "%s %%", b_h);
            if(ui_vpd_label)        lv_label_set_text_fmt(ui_vpd_label, "%s kPa", b_v_ext);
            
            if(ui_vpd_ext_label)    lv_label_set_text(ui_vpd_ext_label, b_v_ext);
            if(ui_leaf_vpd_label)   lv_label_set_text(ui_leaf_vpd_label, b_v_leaf);
        } 
        else {
            // SENSOR ABGEZOGEN (Pseudo-Wert erkannt) -> Zeige Striche
            if(ui_chart_temp_label) lv_label_set_text(ui_chart_temp_label, "--.- °C");
            if(ui_humid_label)      lv_label_set_text(ui_humid_label, "--.- %");
            if(ui_vpd_label)        lv_label_set_text(ui_vpd_label, "-.--");
            
            if(ui_vpd_ext_label)    lv_label_set_text(ui_vpd_ext_label, "-.--");
            if(ui_leaf_vpd_label)   lv_label_set_text(ui_leaf_vpd_label, "-.--");
        }

        // Lüfter RPM Update
        // --- Lüfter RPM Update ---
        int real_rpm = circulation_fan_get_rpm();
        if(ui_circulation_fan_speed_label) {
            if(real_rpm > 50) {
                lv_label_set_text_fmt(ui_circulation_fan_speed_label, "Speed: %d %% (%d RPM)", current_circulation_fan_speed, real_rpm);
            } else {
                lv_label_set_text(ui_circulation_fan_speed_label, "circulation_fan: IDLE / OFF");
            }
        }
        update_battery_ui();
        // NEU: Uhrzeit auf das Label schreiben
        if(ui_time_label) {
            lv_label_set_text(ui_time_label, get_current_time_str().c_str());
        }
    }
    
    if (millis() - last_ble_update > 5000) {
        last_ble_update = millis();
        bleBridge.updateBroadcast(getTempExt(), getExternalHumidity(), getTempIn(), 40.0, 25.5f, get_battery_voltage_now(), circulation_fan_get_rpm());
    }
    yield(); 

}