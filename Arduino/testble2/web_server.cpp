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
#include "plant_planner.h"

extern ESPWatch watch; 

#include "grow_controller.h" 
extern WebServer server;
extern String get_current_time_str();

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
    
    JsonObject health = obj.createNestedObject("health");
    JsonObject signal = health.createNestedObject("signal");
    
    if (WiFi.status() == WL_CONNECTED) {
        signal["rssi"] = WiFi.RSSI();
    } else {
        signal["rssi"] = -256; 
    }

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

    obj["temp_in"] = getTempIn();
    obj["temp_ext"] = getTempExt();
    obj["humid_ext"] = getExternalHumidity();
    obj["humid_in"] = getInternalHumidity();
    obj["leaf_temp"] = 25.5;
    obj["vbat"] = get_battery_voltage_now();
    obj["rev"] = current_rev;
    
    exhaust_fan_get_status(obj);
    circulation_fan_get_status(obj);
    
    // Aufruf matcht jetzt exakt mit dem Prototyp aus plant_planner.h
    obj["rev_plant_planner"] = get_plant_planner_rev();

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

        if (obj.containsKey("rev")) {
            current_rev = obj["rev"]; 
        }

        exhaust_fan_process_json(obj); 
        circulation_fan_process_json(obj);
        plant_planner_process_json(obj);
        light_control_process_json(obj);            
        grow_controller_process_json(obj);       
        StaticJsonDocument<128> res;
        res["status"] = "ok";
        res["rev"] = current_rev; 
        
        String response;
        serializeJson(res, response);
        server.send(200, "application/json", response);
    }
}

void handleGetPlants() {
    if (!server.authenticate(www_username, www_password)) return server.requestAuthentication();
    sendStandardHeaders();

    DynamicJsonDocument doc(8192); 
    JsonObject obj = doc.to<JsonObject>();

    plant_planner_get_status(obj); 

    String response;
    serializeJson(doc, response);
    server.send(200, "application/json", response);
}

void handleControlPlantsJSON() {
    if (!server.authenticate(www_username, www_password)) return server.requestAuthentication();
    sendStandardHeaders();

    if (server.hasArg("plain")) {
        DynamicJsonDocument doc(8192);
        DeserializationError error = deserializeJson(doc, server.arg("plain"));
        if (error) return;

        JsonObject obj = doc.as<JsonObject>();

        plant_planner_process_json(obj); 

        StaticJsonDocument<128> res;
        res["status"] = "ok";
        
        String response;
        serializeJson(res, response);
        server.send(200, "application/json", response);
    }
}

namespace WebModule {
    void _startServerCommon() {
        server.on("/data", handleData);                         
        server.on("/control", HTTP_POST, handleControlJSON);     
        
        server.on("/data/plants", handleGetPlants);              
        server.on("/control/plants", HTTP_POST, handleControlPlantsJSON); 
        
        WebServerBrowser::registerRoutes(server);
        server.begin();
        Serial.println("Webserver gestartet.");
    }

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

    void init_ap(const char* ap_name) {
        WiFi.mode(WIFI_AP);
        WiFi.softAP(ap_name, ""); 
        esp_wifi_set_ps(WIFI_PS_NONE);

        Serial.printf("Hotspot aktiv: %s | IP: 192.168.4.1\n", ap_name);

        _startServerCommon();
    }

    void update() {
        if (WiFi.status() == WL_CONNECTED || (WiFi.getMode() & WIFI_AP)) {
            server.handleClient();
        }
    }
}