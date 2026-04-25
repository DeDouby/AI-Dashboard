
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

#include "web_server.h"
#include "sensor.h"
#include "circulation_fan.h"
#include "exhaust_fan.h"
#include "light_control.h"
#include "power_manager.h"
#include "logic_helper.h"
#include <WiFi.h>
#include "esp_wifi.h"
#include <ArduinoJson.h>
#include "web_server_browser.h"
#include "esp_watch.h"
#include "ble_scanner.h"
extern ESPWatch watch; // Greift auf die Instanz in der Hauptdatei zu

#include "grow_controller.h" // <--- DAS HIER AUCH
extern WebServer server;
extern String get_current_time_str();
// --- DIESE VARIABLEN BRAUCHEN WIR FÜR DIE SENSOREN ---
extern int current_rev;
extern float currentVPD;      
extern float currentVPDIn;    
extern float currentVPDLeaf;
const char* www_username = "admin";
const char* www_password = "1234"; 

void sendStandardHeaders() {
    server.sendHeader("Connection", "close");
    server.sendHeader("Access-Control-Allow-Origin", "*");
}

// 1. DATA ENDPUNKT
void handleData() {
    if (!server.authenticate(www_username, www_password)) return server.requestAuthentication();
    sendStandardHeaders();

    StaticJsonDocument<4096> doc;
    JsonObject obj = doc.to<JsonObject>();
    
    // --- DEINE STRUKTUR (RSSI BLEIBT) ---
    JsonObject health = obj.createNestedObject("health");
    JsonObject signal = health.createNestedObject("signal");
    
    if (WiFi.status() == WL_CONNECTED) {
        signal["rssi"] = WiFi.RSSI();
    } else {
        signal["rssi"] = -256; 
    }

    // --- RTC STATUS & ZEIT (FLACH) ---
    bool isRtcOk = watch.isRTCHealthy();
    obj["rtc_found"] = isRtcOk;

    if (isRtcOk) {
        time_t now;
        struct tm timeinfo;
        time(&now);
        localtime_r(&now, &timeinfo);
        char timeBuf[10];
        sprintf(timeBuf, "%02d:%02d", timeinfo.tm_hour, timeinfo.tm_min);
        obj["rtc_time"] = String(timeBuf);
    } else {
        obj["rtc_time"] = "offline";
    }

    // --- SENSOREN (FLACH) ---
    obj["temp_in"] = getTempIn();
    obj["temp_ext"] = getTempExt();
    obj["humid_ext"] = getExternalHumidity();
    obj["humid_in"] = 40.0;
    obj["leaf_temp"] = 25.5;
    obj["vbat"] = get_battery_voltage_now();
    obj["rev"] = current_rev;
    
    exhaust_fan_get_status(obj);
    circulation_fan_get_status(obj);
    light_control_get_status(obj);
    grow_controller_get_status(obj); 
    BLEScanner::get_status(obj);
    
    String response;
    serializeJson(doc, response);
    server.send(200, "application/json", response);
}
// 2. CONTROL ENDPUNKT
void handleControlJSON() {
    if (!server.authenticate(www_username, www_password)) return server.requestAuthentication();
    sendStandardHeaders();

    if (server.hasArg("plain")) {
        StaticJsonDocument<1024> doc;
        DeserializationError error = deserializeJson(doc, server.arg("plain"));
        if (error) return;

        JsonObject obj = doc.as<JsonObject>();

        // WICHTIG: Die Revision vom Client MUSS global übernommen werden
        if (obj.containsKey("rev")) {
            current_rev = obj["rev"]; 
        }

        // Befehle an Module weiterreichen
        exhaust_fan_process_json(obj); 
        circulation_fan_process_json(obj);
        light_control_process_json(obj);            
        grow_controller_process_json(obj); // Verarbeitet System-Settings       
        StaticJsonDocument<128> res;
        res["status"] = "ok";
        res["rev"] = current_rev; 
        
        String response;
        serializeJson(res, response);
        server.send(200, "application/json", response);
    }
}

// 3. INIT (Muss ganz unten stehen, damit es handleData und handleControlJSON kennt!)
namespace WebModule {
    // Diese interne Hilfsfunktion startet den Server-Kram, der in BEIDEN Modi gleich ist
    void _startServerCommon() {
        server.on("/data", handleData);
        server.on("/control", HTTP_POST, handleControlJSON);
        WebServerBrowser::registerRoutes(server);
        server.begin();
        Serial.println("Webserver gestartet.");
    }

    // MODUS 1: ROUTER (STA) - Dein originaler Code
    void init(const char* ssid, const char* password) {
        WiFi.mode(WIFI_STA);
        WiFi.begin(ssid, password);
        esp_wifi_set_ps(WIFI_PS_NONE);

        Serial.println("WLAN Station Mode -> Warte auf Verbindung & NTP...");

        configTzTime("CET-1CEST,M3.5.0/2,M10.5.0/3", 
                     "de.pool.ntp.org", 
                     "pool.ntp.org", 
                     "time.nist.gov");

        _startServerCommon();
    }

    // MODUS 0: HOTSPOT (AP) - Neu für den Direkt-Modus
    void init_ap(const char* ap_name) {
        WiFi.mode(WIFI_AP);
        WiFi.softAP(ap_name, ""); // Offenes WLAN
        esp_wifi_set_ps(WIFI_PS_NONE);

        Serial.printf("Hotspot aktiv: %s | IP: 192.168.4.1\n", ap_name);

        // Im AP-Modus kein NTP möglich (kein Internet), daher überspringen wir das hier
        _startServerCommon();
    }

    void update() {
        // DER FIX: Der Server muss laufen, wenn wir am Router sind ODER selbst der Hotspot sind
        if (WiFi.status() == WL_CONNECTED || (WiFi.getMode() & WIFI_AP)) {
            server.handleClient();
        }
    }
}