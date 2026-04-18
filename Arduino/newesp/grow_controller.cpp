#include "grow_controller.h"
#include <Preferences.h>
#include <WiFi.h>

Preferences growPrefs;

// Globale System-Variablen
static String _device_name = "GrowBox-Alpha";
static int _log_level = 2; // 0: None, 1: Error, 2: Info, 3: Debug
extern uint32_t device_confirmed_rev; 

void grow_controller_init() {
    growPrefs.begin("grow_ctrl", false);
    _log_level = growPrefs.getInt("log_level", 2);
    _device_name = growPrefs.getString("dev_name", "GrowBox-ESP32");
    
    Serial.println("[GrowController] Initialisiert.");
}

void grow_controller_save_state() {
    growPrefs.putInt("log_level", _log_level);
    growPrefs.putString("dev_name", _device_name);
}

void grow_controller_process_json(JsonObject doc) {
    bool changed = false;

    // 1. SYSTEM SETTINGS
    if (doc.containsKey("log_level")) {
        _log_level = constrain((int)doc["log_level"], 0, 3);
        changed = true;
    }

    if (doc.containsKey("dev_name")) {
        _device_name = doc["dev_name"].as<String>();
        changed = true;
    }

    // 2. REVISION HANDLING (Das Herzstück des Syncs)
    if (doc.containsKey("rev")) {
        device_confirmed_rev = doc["rev"];
        // Wir speichern die Rev nicht zwingend in Preferences, 
        // da sie vom UI bei jedem Connect neu gesetzt wird
    }

    if (changed) {
        grow_controller_save_state();
    }
}

void grow_controller_get_status(JsonObject doc) {
    // System Infos
    doc["dev_name"] = _device_name;
    doc["log_level"] = _log_level;
    doc["rev"] = device_confirmed_rev;
    
    
    // Firmware Info
    doc["fw_ver"] = "v2.4.1-beta";
}