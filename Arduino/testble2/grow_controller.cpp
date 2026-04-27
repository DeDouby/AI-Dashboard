///////////////////////////////////////////////////////////////////////////////
// !!! ABSOLUTES GESETZ: DAS TARGET-REVISION-PRINZIP (C++ / ESP32) !!!
// -------------------------------------------------------------------------
// 1. HARDWARE FOLGT TARGET: Die Loop darf NIEMALS direkt auf UI-Inputs reagieren.
//    Sie vergleicht permanent: 'target_val' vs 'effective_val'.
//
// 2. REVISION-CONFIRMATION: Der ESP32 bestätigt eine Änderung NUR, indem er 
//    die empfangene 'rev' (Revision) im Status-Paket unverändert zurücksendet.
//
// 3. KEINE LÜGEN: Der Status 'Synced' (Grün in der App) darf NUR dann entstehen,
//    wenn 'esp32_rev' == 'ui_target_rev'.
//
// 4. ATOMARE UPDATES: Bei Empfang eines neuen Targets wird die 'rev' sofort 
//    gespeichert, aber der 'effective_val' zieht (ggf. über Rampen) stur nach.
//
// JEDE KI-ÄNDERUNG MUSS DIESE ASYNCHRONE LOGIK WAHREN. DIREKTES ÜBERSCHREIBEN
// VON PINS OHNE TARGET-ABGLEICH IST EIN SYSTEMFEHLER!
///////////////////////////////////////////////////////////////////////////////


#include "grow_controller.h"
#include <WiFi.h>
#include <rom/rtc.h>

// 1. GLOBALE DEFINITION (Ohne static!)
extern int current_rev;
Preferences growPrefs;
String _device_name = "GrowBox-Alpha";
String _wifi_ssid = "";
String _wifi_password = "";
// 2. MODUL-INTERNE VARIABLEN
// Diese werden NICHT im Header mit extern geführt, daher dürfen sie static bleiben
static int _log_level = 2;
static int _wifi_mode = 1; 
static uint32_t grow_controller_rev = 0;
static uint32_t grow_controller_init_rev = 0;



void grow_controller_init() {
    growPrefs.begin("grow", false);
    _wifi_ssid = growPrefs.getString("ssid", ""); // Default leer
    _wifi_password = growPrefs.getString("password", "");
    _device_name = growPrefs.getString("dev_name", "LGS_Grow_Master");
    current_rev = growPrefs.getInt("rev", 0);
}

void grow_controller_save_state() {
    growPrefs.putInt("log_level", _log_level);
    growPrefs.putString("dev_name", _device_name);
    growPrefs.putInt("wifi_mode", _wifi_mode); // Modus sichern
    growPrefs.putString("wifi_ssid", _wifi_ssid);
    growPrefs.putString("wifi_pass", _wifi_password);
}

void grow_controller_process_json(JsonObject doc) {
    bool needs_reboot = false;

    
    // ================= COMMAND HANDLING =================
    if (doc.containsKey("command")) {
        String cmd = doc["command"].as<String>();
    
        Serial.print("Command erhalten: ");
        Serial.println(cmd);
    
        if (cmd == "soft_reset") {
            Serial.println("Soft Reset...");
            delay(500);
            ESP.restart();
        }
    
        else if (cmd == "factory_reset") {
            Serial.println("Factory Reset...");
            growPrefs.clear();   // 🔥 ALLES LÖSCHEN
            delay(500);
            ESP.restart();
        }
    
        else if (cmd == "sync_time") {
            Serial.println("Sync Time Trigger");
            // 👉 hier ggf. NTP oder RTC sync triggern
        }
    
        else if (cmd == "test") {
            Serial.println("Test Command OK");
        }
    }    
    // Falls neue WiFi Daten kommen
    if (doc.containsKey("wifi_ssid")) {
        String new_ssid = doc["wifi_ssid"].as<String>();
        growPrefs.putString("ssid", new_ssid);
        _wifi_ssid = new_ssid;
        needs_reboot = true; 
    }

    if (doc.containsKey("wifi_pw")) {
        String new_pw = doc["wifi_pw"].as<String>();
        growPrefs.putString("password", new_pw);
        _wifi_password = new_pw;
        needs_reboot = true;
    }

    if (doc.containsKey("wifi_mode")) {
        int mode = doc["wifi_mode"];
        growPrefs.putInt("wifi_mode", mode);
        _wifi_mode = mode;   // 🔥 FEHLT BEI DIR
        needs_reboot = true;
    }

    // Nach dem Speichern der Revision (Gesetz Punkt 4)
    if (doc.containsKey("rev_grow")) {
        grow_controller_rev = doc["rev_grow"];
    }
    if (needs_reboot) {
        Serial.println("WiFi Config erhalten. Neustart in 2 Sekunden...");
        delay(2000);
        ESP.restart();
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
    // Standardmäßig 0 (AP), wenn nichts gespeichert ist
    return growPrefs.getInt("wifi_mode", 0); 
}