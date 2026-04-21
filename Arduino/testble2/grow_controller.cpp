#include "grow_controller.h"
#include <WiFi.h>
#include <rom/rtc.h>

// 1. GLOBALE DEFINITION (Ohne static!)
Preferences growPrefs;
String _device_name = "GrowBox-Alpha";

// 2. MODUL-INTERNE VARIABLEN
// Diese werden NICHT im Header mit extern geführt, daher dürfen sie static bleiben
static int _log_level = 2;
static int _wifi_mode = 1; 
static uint32_t grow_controller_rev = 0;
static uint32_t grow_controller_init_rev = 0;



void grow_controller_init() {
    growPrefs.begin("grow_ctrl", false);
    _log_level = growPrefs.getInt("log_level", 2);
    _device_name = growPrefs.getString("dev_name", "GrowBox-Alpha");
    _wifi_mode = growPrefs.getInt("wifi_mode", 1); 
    
    grow_controller_init_rev = millis() + 1;
    grow_controller_rev = grow_controller_init_rev;
}

void grow_controller_save_state() {
    growPrefs.putInt("log_level", _log_level);
    growPrefs.putString("dev_name", _device_name);
    growPrefs.putInt("wifi_mode", _wifi_mode); // Modus sichern
}

void grow_controller_process_json(JsonObject doc) {
    bool changed = false;
    uint32_t received_rev = 0;

    // === REVISION CHECK ===
    if (doc.containsKey("rev_grow")) {           // <--- WICHTIG: rev_grow
        received_rev = doc["rev_grow"];
    }
    // In grow_controller_process_json() den Befehl zum Umschalten einbauen:

    // Nur verarbeiten wenn die Revision neu ist
    if (received_rev > grow_controller_rev) {
        grow_controller_rev = received_rev;

        
        // 🔥 WIFI MODE HIER REIN!
        if (doc.containsKey("wifi_mode")) {
            int new_mode = doc["wifi_mode"];
            if (new_mode != _wifi_mode && (new_mode == 0 || new_mode == 1)) {
                _wifi_mode = new_mode;
                grow_controller_save_state();
                
                Serial.printf("[GrowController] WiFi Mode auf %d geändert → Reboot!\n", new_mode);
                Serial.flush();           // <--- WICHTIG
                delay(800);               // Etwas länger für Flash
                ESP.restart();
            }
        }   
        // 1. System Settings
        if (doc.containsKey("dev_name")) {
            _device_name = doc["dev_name"].as<String>();
            changed = true;
        }

        if (doc.containsKey("log_level")) {
            _log_level = constrain((int)doc["log_level"], 0, 3);
            changed = true;
        }

        // === COMMANDS ===
        if (doc.containsKey("command")) {
            String cmd = doc["command"].as<String>();

            if (cmd == "soft_reset") {
                Serial.println("[GrowController] Soft Reset commanded");
                delay(100);
                ESP.restart();
            }
            else if (cmd == "factory_reset") {
                Serial.println("[GrowController] FACTORY RESET commanded!");
                growPrefs.clear();
                delay(500);
                ESP.restart();
            }
            else if (cmd == "sync_time") {
                Serial.println("[GrowController] Sync Time requested");
                // Hier später RTC Sync einbauen
            }
            else if (cmd == "test" || cmd == "noop" || cmd == "ping") {   // <--- NEU
                Serial.printf("[GrowController] Test command received - Rev accepted: %u\n", received_rev);
                changed = true;        // damit unten gespeichert wird (optional)
            }
            else if (cmd == "reboot") {
                Serial.println("[GrowController] Reboot commanded");
                delay(100);
                ESP.restart();
            }
        }
    }

    // Auch bei purem Test-Command die Rev als bestätigt markieren
    if (doc.containsKey("command")) {
        String cmd = doc["command"].as<String>();
        if (cmd == "test" || cmd == "noop" || cmd == "ping") {
            if (changed) grow_controller_save_state();
            Serial.printf("[GrowController] Rev updated via test command → %u\n", grow_controller_rev);
        }
    }
}

void grow_controller_get_status(JsonObject doc) {
    // System Infos
    doc["dev_name"] = _device_name;
    doc["log_level"] = _log_level;
    
    doc["uptime_esp_s"] = millis() / 1000;
    doc["fw_ver"] = "v2.4.1-beta";
    
    // IP + WLAN
    
    
    if (WiFi.status() == WL_CONNECTED) {
        doc["ip"] = WiFi.localIP().toString();
        doc["ssid"] = WiFi.SSID();
        doc["rssi"] = WiFi.RSSI();
    } else {
        doc["ip"] = "Not connected";
        doc["ssid"] = "";
        doc["rssi"] = 0;
    }

    // Heap Monitoring
    doc["free_heap"]   = ESP.getFreeHeap();
    doc["max_alloc"]   = ESP.getMaxAllocHeap();
    doc["heap_usage"]  = ESP.getHeapSize() - ESP.getFreeHeap();

    // Boot Cause
    int reason = (int)rtc_get_reset_reason(0);
    if (reason == 1)      doc["boot_cause"] = "Power Cut / Hard Reset";
    else if (reason == 12) doc["boot_cause"] = "Software Reboot";
    else if (reason == 3)  doc["boot_cause"] = "Software Crash (Watchdog)";
    else                   doc["boot_cause"] = "Other: " + String(reason);

    // === REVISIONEN ZURÜCKSENDEN (genau wie bei circfan) ===
    doc["rev_grow"] = grow_controller_rev;           // <--- Modulspezifisch
    doc["rev_init_grow"] = grow_controller_init_rev; // <--- Init Rev
    doc["wifi_mode"] = _wifi_mode;


}

int grow_controller_get_wifi_mode() {
    growPrefs.begin("grow_ctrl", true);
    int mode = growPrefs.getInt("wifi_mode", 1); 
    growPrefs.end();
    return mode;
}