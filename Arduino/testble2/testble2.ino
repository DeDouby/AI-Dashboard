#include "power_manager.h"
#include "sensor.h"
#include "ble_bridge.h"
#include "logic_helper.h"
#include "hardware_init.h"
#include "circulation_fan.h" 
#include "exhaust_fan.h" 
#include "config.h"
#include "web_server.h" // Modul einbinden
#include "light_control.h"
#include "grow_controller.h" // <--- DAS HIER AUCH
#include "esp_watch.h"
#include "esp_sntp.h"
#include "ble_scanner.h"
// BLE & System
ESPWatch watch;
BLEBridge bleBridge;
uint32_t device_confirmed_rev = 0;



// DIE EINZIGE DEFINITION DES SERVERS
WebServer server(80); 
// Hardware & Sensoren (MÜSSEN hier bleiben für die anderen .cpp Dateien!)
TwoWire I2C_Sensor = TwoWire(0); // Bus 0 für Sensoren            
TwoWire I2C_RTC    = TwoWire(1); // Bus 1 für RTC (Eigener Bus!)
Adafruit_SHT31 sht31 = Adafruit_SHT31(&I2C_Sensor); 
bool externalSensorFound = false;
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
    // 1. System-Basis
    setCpuFrequencyMhz(240);
    Serial.begin(115200);
    init_hardware();

    // 2. ABSOLUTE PRIORITÄT: HARDWARE INIT
    // Zuerst die Preferences laden, damit wir wissen, wie hell das Licht sein soll
    grow_controller_init(); 
    
    // JETZT SOFORT das Licht und die Lüfter anwerfen (VOR dem WLAN!)

    
    Serial.println(">>> Hardware läuft (Pflanzen versorgt) <<<");

    // 3. INFRASTRUKTUR
    BLEDevice::init("LGS_Grow_Master");
    if (watch.begin(I2C_RTC)) {
        Serial.println("RTC gefunden");
    }

    // 4. NETZWERK (Darf jetzt so lange blockieren wie es will)
    int wifi_mode = grow_controller_get_wifi_mode();
    if (wifi_mode == 0 || _wifi_ssid == "" || _wifi_ssid == "NULL") {
        Serial.println(">>> AP-MODUS <<<");
        WebModule::init_ap(_device_name.c_str());
    } else {
        Serial.printf(">>> Verbinde: %s <<<\n", _wifi_ssid.c_str());
        WebModule::init(_wifi_ssid.c_str(), _wifi_password.c_str());
    }

    // 5. BACKGROUND SERVICES
    configTzTime("CET-1CEST,M3.5.0/2,M10.5.0/3", "pool.ntp.org", "time.nist.gov");
    light_init();
    circulation_fan_init(PIN_CIRC_FAN, PIN_CIRC_TACHO);
    exhaust_fan_init(PIN_EXH_FAN, PIN_EXH_TACHO);externalSensorFound = initExternalSensor();
    power_manager_init();
    BLEScanner::init();   
    bleBridge.begin();

    Serial.println("System vollständig bereit.");
}
// ---------- LOOP ----------
// ---------- LOOP ----------
void loop() {
    WebModule::update();           // Web-Server muss laufen bleiben!

    circulation_fan_update(); 
    exhaust_fan_update(); 
    light_update();
    power_manager_update();
    BLEScanner::update(); // 3. Den Scanner am Leben erhalten
    // ==================== ZEIT-MANAGEMENT ====================
    static uint32_t last_time_check = 0;
    static bool initial_sync_done = false;

    static uint32_t last_sync = 0;
    
    if (millis() - last_sync > 15000) {
        last_sync = millis();
    
        if (WiFi.status() == WL_CONNECTED) {
            struct tm timeinfo;
            if (getLocalTime(&timeinfo, 2000)) {
                if (!initial_sync_done) {
                    Serial.println("NTP Sync → schreibe in RTC");
                    watch.writeToRTC();        // Systemzeit → RTC
                    initial_sync_done = true;
                }
                // Optional: alle 6 Stunden RTC mit Systemzeit abgleichen
                else if (millis() > 6*3600*1000UL) {
                    watch.writeToRTC();
                }
            }
        }
    
        // Immer RTC als Backup nutzen, falls Systemzeit kaputt
        if (time(nullptr) < 946684800 && watch.isRTCHealthy()) {
            watch.syncFromRTC();
        }
    }
    
    // Statt direkt pBLEScan->stop() zu benutzen:
    static uint32_t lastBLErestart = 0;
    
    if (millis() - lastBLErestart > 2*3600*1000UL) {   // alle 2 Stunden
        lastBLErestart = millis();
        BLEScanner::restart();        // ← So geht's sauber
    }
    
    static bool light_boot_synced = false;
    if (!light_boot_synced) {
        if (time(nullptr) > 946684800) {
            light_update();   // FORCE derived state build
            light_boot_synced = true;
            Serial.println("LIGHT BOOT SYNC EXECUTED");
        }
    }
    // BLE Broadcast (alle 5 Sek)
    // Im loop() Bereich für BLE Broadcast
    static uint32_t last_ble_broadcast = 0;
    if (millis() - last_ble_broadcast > 5000) {
        last_ble_broadcast = millis();
        
        // Nur kurz broadcasten, damit wir den Rest der Zeit für WiFi & Scan frei haben
        bleBridge.updateBroadcast(
            getTempExt(), getExternalHumidity(), getTempIn(),
            40.0, 25.5f, get_battery_voltage_now(),
            circulation_fan_get_rpm()
        );
    }

    yield();
}