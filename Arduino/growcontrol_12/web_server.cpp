
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

extern WebServer server;

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

    StaticJsonDocument<1024> doc;
    JsonObject obj = doc.to<JsonObject>();

    // Sensoren (Direkt aus sensor.h / globals)
    obj["temp_in"] = getTempIn();
    obj["temp_ext"] = getTempExt();
    obj["humid_ext"] = getExternalHumidity();
    obj["humid_in"] = 40.0;
    obj["vpd_ext"] = currentVPD;
    obj["vpd_in"] = currentVPDIn;
    obj["vpd_leaf"] = currentVPDLeaf;
    obj["vbat"] = get_battery_voltage_now();
    obj["rev"] = current_rev;

    // Module befüllen den Rest
    exhaust_fan_get_status(obj);
    circulation_fan_get_status(obj);
    light_control_get_status(obj);

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

        // Antwort direkt mit der NEUEN Revision
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
    void init(const char* ssid, const char* password) {
        WiFi.mode(WIFI_STA);
        WiFi.begin(ssid, password);
        esp_wifi_set_ps(WIFI_PS_NONE);
        configTzTime("CET-1CEST,M3.5.0,M10.5.0", "pool.ntp.org", "time.google.com");
        
        server.on("/data", handleData);
        server.on("/control", HTTP_POST, handleControlJSON); // JETZT FEHLERFREI
        WebServerBrowser::registerRoutes(server);
        server.begin();
    }

    void update() {
        if (WiFi.status() == WL_CONNECTED) server.handleClient();
    }
}