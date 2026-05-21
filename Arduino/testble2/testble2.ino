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
#include "esp_sntp.h" // WICHTIG für sntp_get_sync_status()
#include "system_reset.h"    // <--- 1. NEUES RESET MODUL INCLUDIEREN
#include "plant_planner.h"  // <--- 1. NEUES PLANT PLANNER MODUL INCLUDIEREN
// BLE & System
ESPWatch watch;
BLEBridge bleBridge;
uint32_t device_confirmed_rev = 0;



// DIE EINZIGE DEFINITION DES SERVERS
WebServer server(80); 
// Hardware & Sensoren (MÜSSEN hier bleiben für die anderen .cpp Dateien!)
TwoWire I2C_Sensor = TwoWire(0); // Bus 0 für Sensoren            
TwoWire I2C_RTC    = TwoWire(1); // Bus 1 für RTC (Eigener Bus!)

extern Adafruit_SHT31 sht31_ext;
extern Adafruit_SHT31 sht31_int;

extern bool externalSensorFound;
extern bool internalSensorFound;
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

    SystemReset::init(PIN_RESET_BUTTON); // <--- 2. RESET KNOPF INITIALISIEREN
    // 2. ABSOLUTE PRIORITÄT: HARDWARE INIT & ZEITBASIS
    grow_controller_init(); // Lädt Preferences
    
    // RTC starten und SOFORT prüfen
    if (watch.begin(I2C_RTC)) {
        Serial.println("RTC Hardware gefunden.");
        
        if (watch.isRTCSet()) {
            Serial.println("RTC Register-Validierung: OK. Synchronisiere Systemzeit...");
            watch.syncFromRTC(); // Uhrzeit läuft, lade sie in den ESP32
        } else {
            Serial.println("WARNUNG: RTC meldet OSF-Flag! Uhr ist ungesetzt (Batterie leer/Fabrikneu). Wait for NTP.");
            // Wir laden die RTC-Zeit NICHT, da sie Schrott ist. Systemuhr bleibt auf 1970 Boot-Basis.
        }
    } else {
        Serial.println("CRITICAL: RTC Hardware nicht auf dem I2C-Bus gefunden!");
    }

    // JETZT das Licht-Modul starten. Es findet entweder die RTC-Zeit vor, 
    // oder sieht das Jahr 1970 und bleibt im sicheren AUS-Zustand.
    light_init();
    
    Serial.println(">>> Hardware läuft (Zeitbasis initialisiert) <<<");

    // 3. INFRASTRUKTUR
    BLEDevice::init("LGS_Grow_Master");

    // 4. NETZWERK
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
    
    circulation_fan_init(PIN_CIRC_FAN, PIN_CIRC_TACHO);
    exhaust_fan_init(PIN_EXH_FAN, PIN_EXH_TACHO);
    plant_planner_init();
    externalSensorFound = sht31_ext.begin(0x44);
    internalSensorFound = sht31_int.begin(0x44);
    
    if (externalSensorFound) Serial.println("EXT SHT31 OK (Bus0)");
        else Serial.println("EXT SHT31 FEHLT");
    
    if (internalSensorFound) Serial.println("INT SHT31 OK (Bus1)");
        else Serial.println("INT SHT31 FEHLT");
        
    power_manager_init();
    BLEScanner::init();   
    bleBridge.begin();

    Serial.println("System vollständig bereit.");
}
// ---------- LOOP ----------
// ---------- LOOP ----------

void loop() {
    WebModule::update();           // Web-Server am Leben erhalten
    SystemReset::update();         // <--- 3. PERMANENT DEN KNOPF ÜBERWACHEN
    circulation_fan_update(); 
    exhaust_fan_update(); 
    light_control_set_humidity(getInternalHumidity());
    light_update();                // Berechnet stur den Lichtzustand anhand der Systemzeit
    power_manager_update();
    BLEScanner::update(); 

    // ==================== ZEIT-MANAGEMENT (PROFI-VERSION) ====================
    static uint32_t last_rtc_sync = 0;
    
    // Bedingung für RTC-Update: 
    // Entweder es ist eine Stunde vergangen (Routine-Abgleich)
    // ODER wir haben Internetzeit und die RTC meldet hardwareseitig, dass sie ungesetzt ist (Sofort-Heilung!)
    if ((millis() - last_rtc_sync > 3600000) || (sntp_get_sync_status() == SNTP_SYNC_STATUS_COMPLETED && !watch.isRTCSet())) { 
        
        if (sntp_get_sync_status() == SNTP_SYNC_STATUS_COMPLETED) {
            Serial.println("Zeitmanagement: NTP-Zeit valide. Aktualisiere Hardware-RTC & lösche OSF...");
            watch.writeToRTC();       // Schreibt Internetzeit in DS3231 und löscht OSF-Flag
            last_rtc_sync = millis(); // Timer zurücksetzen
        }
    }

    // KRISENVORSORGE: Falls die Systemuhr im Betrieb durch einen Software-Glitch auf 1970 fällt,
    // holen wir uns die Rettung aus der RTC (aber nur, wenn die RTC auch gestellt ist!)
    static uint32_t last_backup_check = 0;
    if (millis() - last_backup_check > 60000) { 
        last_backup_check = millis();
        if (time(nullptr) < 946684800 && watch.isRTCHealthy() && watch.isRTCSet()) { 
            Serial.println("NOTFALL: Systemzeit korrupt! Synchronisiere sofort mit intakter RTC...");
            watch.syncFromRTC();
        }
    }
    
    // ==================== BLE SCANNER RESTART ====================
    static uint32_t lastBLErestart = 0;
    if (millis() - lastBLErestart > 2*3600*1000UL) {   // alle 2 Stunden
        lastBLErestart = millis();
        BLEScanner::restart();        
    }
    
    // ==================== BLE BROADCAST (alle 5 Sek) ====================
    static uint32_t last_ble_broadcast = 0;
    if (millis() - last_ble_broadcast > 5000) {
        last_ble_broadcast = millis();
        
        bleBridge.updateBroadcast(
            getTempExt(),            
            getExternalHumidity(),   
            getTempIn(),             
            getInternalHumidity(),   
            25.5f,                   
            get_battery_voltage_now(), 
            circulation_fan_get_rpm()
        );
    }

    yield();
}