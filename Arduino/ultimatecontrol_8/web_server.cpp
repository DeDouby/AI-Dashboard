#include "web_server.h"
#include "sensor.h"
#include "fan.h"
#include "power_manager.h"
#include "logic_helper.h"
#include <WiFi.h>
#include "esp_wifi.h"
#include <ArduinoJson.h>
#include "web_server_browser.h"
#include "light_control.h"

extern WebServer server;
extern int current_fan_speed;
extern int current_fan_min_speed;
extern FanMode current_fan_mode;
extern float currentVPD;      
extern float currentVPDIn;    
extern float currentVPDLeaf;  
extern LightMode current_light_mode;
// LIGHT CONTROL STATE (FIX)
extern int target_brightness;
extern time_t light_start_unix;
extern uint32_t light_duration_sec;
// NEU: Timer-Variablen für JSON Zugriff
extern LightMode current_light_mode;
const char* www_username = "admin";
const char* www_password = "1234"; 
extern int current_rev; // NU
extern uint32_t sunrise_offset_sec; // Neu hinzugefügt
void sendStandardHeaders() {
    server.sendHeader("Connection", "close");
    server.sendHeader("Access-Control-Allow-Origin", "*");
}

// --- DATA ENDPUNKT REPARIERT ---
// --- DATA ENDPUNKT FINAL STABILISIERT ---
void handleData() {
    if (!server.authenticate(www_username, www_password)) {
        return server.requestAuthentication();
    }

    sendStandardHeaders();

    // Wir nutzen ArduinoJson, um Speicherfragmente zu vermeiden (Fix für Bootloop)
    StaticJsonDocument<1024> doc;

    // Sensordaten
    doc["temp_in"] = getTempIn();
    doc["temp_ext"] = getTempExt();
    doc["humid_ext"] = getExternalHumidity();
    doc["humid_in"] = 40.0;           // <--- NEU: Fix für die Konsistenz zum Decoder
    doc["vpd_ext"] = currentVPD;
    doc["rpm"] = fan_get_rpm();
    doc["fan_pct"] = current_fan_speed;
    doc["fan_min"] = current_fan_min_speed;
        // FAN MODE FIX
    if (current_fan_mode == FAN_MODE_NATURAL) {
        doc["fan_mode"] = "nat";
    } else if (current_fan_mode == FAN_MODE_CHAOTIC) {
        doc["fan_mode"] = "chao";
    } else {
        doc["fan_mode"] = "man";
    }
    doc["vbat"] = get_battery_voltage_now();
    doc["vpd_leaf"] = currentVPDLeaf;
    doc["vpd_in"] = currentVPDIn;

    // Licht-Status
    doc["light_target"] = target_brightness;
    doc["light_pct"] = light_get_effective_brightness();
    doc["light_mode"] = (current_light_mode == LIGHT_MODE_TIMER) ? "tim" : "man";
    doc["light_sunrise_min"] = (int)(sunrise_offset_sec / 60);
    // NEU: Die Restminuten mitschicken
    doc["light_remaining"] = light_get_minutes_to_next_change();
    // --- ZEIT-FIX FÜR DIE UI ---
    // Zeit-Fix für UI
    struct tm ti_start;
    localtime_r(&light_start_unix, &ti_start);
    doc["light_timer_start_h"] = ti_start.tm_hour;
    doc["light_timer_start_m"] = ti_start.tm_min;
    doc["light_timer_start"] = ti_start.tm_hour;
    doc["light_timer_dur"] = (int)(light_duration_sec / 3600);
    doc["rev"] = current_rev;

    String response;
    serializeJson(doc, response);
    server.send(200, "application/json", response);
}
// --- CONTROL ENDPUNKT BEREINIGT ---
// --- CONTROL ENDPUNKT ---
void handleControlJSON() {
    if (!server.authenticate(www_username, www_password)) {
        return server.requestAuthentication();
    }

    sendStandardHeaders();

    if (server.hasArg("plain")) {
        StaticJsonDocument<300> doc;
        deserializeJson(doc, server.arg("plain"));

        // REV
        if (doc.containsKey("rev")) {
            current_rev = doc["rev"];
            Serial.print("Neue Revision empfangen: ");
            Serial.println(current_rev);
        }

        // --- FAN BEREICH ANPASSEN ---
        if (doc.containsKey("fan_pct")) {
            int val = constrain((int)doc["fan_pct"], 0, 100);
            // VORHER: current_fan_speed = val; 
            // JETZT: Nutze den Setter, der auch speichert!
            fan_set_speed(val); 
        }

        if (doc.containsKey("fan_min")) {
            int val = constrain((int)doc["fan_min"], 0, 100);
            // NEU: Wir rufen die neue Setter-Funktion auf
            fan_set_min_speed(val); 
        }

        if (doc.containsKey("fan_mode")) {
            String mode = doc["fan_mode"];
            if (mode == "nat") fan_set_mode(FAN_MODE_NATURAL);
            else if (mode == "chao") fan_set_mode(FAN_MODE_CHAOTIC);
            else fan_set_mode(FAN_MODE_MANUAL);
            // fan_set_mode ruft intern bereits fan_save_state auf!
        }

        // -------------------------
        // LIGHT (STABLE & DECOUPLED LOGIC)
        // -------------------------
        if (doc.containsKey("light_stop") && (int)doc["light_stop"] == 1) {
            // STOP/OFF: Harter Reset auf Manuell 0%
            light_set_mode(LIGHT_MODE_MANUAL);
            light_set_brightness(0);
        } 
        else {
            // 1. TIMER-DATEN (Falls vorhanden, initialisieren wir den Timer)
            // Im Webserver (handleControlJSON)
            if (doc.containsKey("l_start_h") && doc.containsKey("l_dur")) {
                int start_h = doc["l_start_h"];
                int start_m = doc.containsKey("l_start_m") ? (int)doc["l_start_m"] : 0;
                int duration = doc["l_dur"];
                
                // Wir setzen die globale Variable direkt - der Webserver DARF das, 
                // weil er die 'extern' Deklaration hat.
                int sun_min = doc.containsKey("l_sun") ? (int)doc["l_sun"] : (sunrise_offset_sec / 60);
                sunrise_offset_sec = (uint32_t)sun_min * 60; 
            
                // Wir rufen die Funktion GENAU SO auf, wie sie im Header steht (3 Parameter)
                light_set_timer(start_h, start_m, duration);
            }


            // 2. MODUS-WECHSEL (Nur wenn explizit angefordert)
            if (doc.containsKey("light_mode")) {
                String lmode = doc["light_mode"];
                if (lmode == "brth") {
                    light_set_mode(LIGHT_MODE_BREATH);
                } else if (lmode == "flicker") {
                    light_set_mode(LIGHT_MODE_FLICKER);
                } else if (lmode == "tim") {
                    // Wechsel in Timer-Modus nur, wenn ein gültiger Startpunkt existiert
                    if (light_start_unix > 0) light_set_mode(LIGHT_MODE_TIMER);
                } else if (lmode == "man") {
                    light_set_mode(LIGHT_MODE_MANUAL);
                }
            }

            // 3. HELLIGKEIT (Slider-Input)
            // Diese Zeile ist jetzt entkoppelt: Sie ändert NUR target_brightness.
            // Der Timer nutzt diesen Wert dann bei seinem nächsten Update automatisch.
            if (doc.containsKey("light_pct")) {
                int val = doc["light_pct"];
                light_set_brightness(constrain(val, 0, 100));
            }
        }

        // --- RESPONSE ---
        StaticJsonDocument<128> res;
        res["status"] = "ok";
        res["rev"] = current_rev;

        String response;
        serializeJson(res, response);
        server.send(200, "application/json", response);
    }
}

namespace WebModule {
    void init(const char* ssid, const char* password) {
        WiFi.mode(WIFI_STA);
        WiFi.begin(ssid, password);
        esp_wifi_set_ps(WIFI_PS_NONE);

        configTzTime("CET-1CEST,M3.5.0,M10.5.0", "pool.ntp.org", "time.google.com");

        server.on("/data", handleData);
        server.on("/data", handleData);
        server.on("/control", HTTP_POST, handleControlJSON);
        WebServerBrowser::registerRoutes(server);

        server.begin();
        Serial.println("Webserver fixed.");
    }

    void update() {
        if (WiFi.status() == WL_CONNECTED) {
            server.handleClient();
        }
    }
}