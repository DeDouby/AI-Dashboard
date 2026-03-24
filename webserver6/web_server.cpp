#include "web_server.h"
#include "sensor.h"
#include "fan.h"
#include "power_manager.h"
#include "logic_helper.h"
#include <WiFi.h>
#include "esp_wifi.h"
#include <ArduinoJson.h>

extern WebServer server;
extern int current_fan_speed;
extern FanMode current_fan_mode;
extern float currentVPD;      
extern float currentVPDIn;    
extern float currentVPDLeaf;  

// --- HILFSFUNKTION FÜR STABILE VERBINDUNG ---
void sendStandardHeaders() {
    server.sendHeader("Connection", "close");
    server.sendHeader("Access-Control-Allow-Origin", "*");
}

// --- NEUER JSON CONTROL HANDLER (Für die App) ---
void handleControlJSON() {
    sendStandardHeaders();
    if (server.hasArg("plain")) {
        StaticJsonDocument<256> doc;
        DeserializationError error = deserializeJson(doc, server.arg("plain"));

        if (!error) {
            // 1. Fan Speed prüfen
            if (doc.containsKey("fan_pct")) {
                int val = doc["fan_pct"];
                val = constrain(val, 0, 100);
                fan_set_speed(val);
                current_fan_speed = val;
            }

            // 2. Modus prüfen
            if (doc.containsKey("mode")) {
                String mode = doc["mode"];
                if (mode == "nat") fan_set_mode(FAN_MODE_NATURAL);
                else if (mode == "chao") fan_set_mode(FAN_MODE_CHAOTIC);
                else if (mode == "man") fan_set_mode(FAN_MODE_MANUAL);
            }
            server.send(200, "application/json", "{\"status\":\"ok\"}");
        } else {
            server.send(400, "application/json", "{\"status\":\"error\"}");
        }
    }
}

// --- KLASSISCHE BROWSER HANDLER ---
void handleSetMode() {
    if (server.hasArg("mode")) {
        String mode = server.arg("mode");
        if (mode == "nat") fan_set_mode(FAN_MODE_NATURAL);
        else if (mode == "chao") fan_set_mode(FAN_MODE_CHAOTIC);
        else fan_set_mode(FAN_MODE_MANUAL);
    }
    server.sendHeader("Location", "/");
    server.send(303);
}

void handleSetFan() {
    if (server.hasArg("value")) {
        int val = server.arg("value").toInt();
        fan_set_speed(val); 
        current_fan_speed = val;
    }
    server.sendHeader("Location", "/");
    server.send(303); 
}

void handleRoot() {
    float t_in = getTempIn();
    float t_ext = getTempExt();
    int rpm = fan_get_rpm();

    String html;
    html.reserve(2500);
    html = "<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>";
    html += "<style>body{font-family:sans-serif;text-align:center;padding:10px;background:#f4f4f4;}";
    html += ".card{background:white;padding:15px;border-radius:10px;margin-bottom:10px;box-shadow:0 2px 5px rgba(0,0,0,0.1);}";
    html += ".val{font-weight:bold;color:#007bff;} .btn{padding:10px;margin:5px;border:none;border-radius:5px;background:#007bff;color:white;text-decoration:none;display:inline-block;}";
    html += ".active{background:#28a745;} .slider{width:80%;height:25px;}</style></head><body>";
    html += "<h1>Grow-Control Center</h1>";
    html += "<div class='card'><h2>Klima</h2><p>Innen: <span class='val'>" + String(t_in, 1) + "&deg;C</span></p></div>";
    html += "<div class='card'><h2>Luefter</h2><p><span class='val'>" + String(current_fan_speed) + "% (" + String(rpm) + " RPM)</span></p>";
    html += "<form action='/set_fan' method='get'><input type='range' name='value' min='0' max='100' value='" + String(current_fan_speed) + "' class='slider' onchange='this.form.submit()'></form>";
    html += "<div><a href='/set_mode?mode=man' class='btn " + String(current_fan_mode == FAN_MODE_MANUAL ? "active" : "") + "'>MAN</a>";
    html += "<a href='/set_mode?mode=nat' class='btn " + String(current_fan_mode == FAN_MODE_NATURAL ? "active" : "") + "'>NAT</a>";
    html += "<a href='/set_mode?mode=chao' class='btn " + String(current_fan_mode == FAN_MODE_CHAOTIC ? "active" : "") + "'>CHAO</a></div></div>";
    html += "</body></html>";
    server.send(200, "text/html", html);
}

// --- DATA ENDPUNKT (Original Namen!) ---
void handleData() {
    sendStandardHeaders();
    String json;
    json.reserve(600); // Etwas mehr Puffer für den Modus-String
    json = "{";
    json += "\"temp_in\":"    + String(getTempIn(), 2) + ",";
    json += "\"temp_ext\":"   + String(getTempExt(), 2) + ",";
    json += "\"temp_leaf\":"  + String(getTempExt(), 2) + ","; 
    json += "\"humid_in\":40.0,"; 
    json += "\"humid_ext\":"  + String(getExternalHumidity(), 1) + ",";
    json += "\"vpd_ext\":"    + String(currentVPD, 2) + ",";
    json += "\"vpd_in\":"     + String(currentVPDIn, 2) + ",";
    json += "\"vpd_leaf\":"   + String(currentVPDLeaf, 2) + ",";
    json += "\"rpm\":"         + String(fan_get_rpm()) + ",";
    json += "\"fan_pct\":"     + String(current_fan_speed) + ",";
    json += "\"vbat\":"        + String(get_battery_voltage_now(), 2) + ",";
    
    // NEU: Den Modus als String mitschicken
    String mStr = "man";
    if (current_fan_mode == FAN_MODE_NATURAL) mStr = "nat";
    else if (current_fan_mode == FAN_MODE_CHAOTIC) mStr = "chao";
    json += "\"mode\":\""      + mStr + "\""; 
    
    json += "}";
    server.send(200, "application/json", json);
}

namespace WebModule {
    void init(const char* ssid, const char* password) {
        WiFi.mode(WIFI_STA);
        WiFi.begin(ssid, password);
        esp_wifi_set_ps(WIFI_PS_NONE); // Power-Save OFF für schnelle Antwort

        server.on("/", handleRoot);
        server.on("/set_fan", handleSetFan);
        server.on("/set_mode", handleSetMode);
        server.on("/data", handleData);
        server.on("/control", HTTP_POST, handleControlJSON); // Der Pfad für die App

        server.begin();
        Serial.println("Webserver vollständig bereit.");
    }

    void update() {
        if (WiFi.status() == WL_CONNECTED) {
            server.handleClient();
        }
    }
}