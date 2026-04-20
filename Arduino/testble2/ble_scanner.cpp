#include "ble_scanner.h"
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include "freertos/FreeRTOS.h"
#include "freertos/portmacro.h"

portMUX_TYPE ble_mux = portMUX_INITIALIZER_UNLOCKED;



// --- DEINE ORIGINALEN WERTE (FÜR STABILEN EMPFANG) ---
const int SCAN_TIME = 1; 
unsigned long lastScanTime = 0;
const unsigned long SCAN_INTERVAL = 2000; 
const unsigned long SENSOR_WATCHDOG_MS = 60000; 

BLEScan* pBLEScan = nullptr;

struct SensorData {
    float temp = -256.0;
    float humid = -256.0;
    int packet = -1;
    unsigned long lastSeen = 0;
    bool is_online = false;
};

static SensorData sps; // Inkbird
static SensorData tb2; // ThermoBeacon

float parseValue(const uint8_t* data, int offset, float scale) {
    int16_t raw = data[offset] | (data[offset + 1] << 8);
    return (float)raw / scale;
}

// Callback Klasse: Verarbeitet Daten im Hintergrund
class MyScannerCallbacks: public BLEAdvertisedDeviceCallbacks {
    void onResult(BLEAdvertisedDevice device) {
        String addr = device.getAddress().toString().c_str();
        unsigned long currentMillis = millis();

        if (device.haveManufacturerData()) {
            String mData = device.getManufacturerData();
            size_t len = mData.length();

            uint8_t payload[32];
            if (len > sizeof(payload)) return;

            memcpy(payload, mData.c_str(), len);

            // SPS Decoder (Inkbird)
            if (addr == "49:25:08:23:07:21" && len >= 7) {
                portENTER_CRITICAL(&ble_mux);
                sps.temp = parseValue(payload, 0, 100.0);
                sps.humid = parseValue(payload, 2, 100.0);
                sps.packet = payload[6];
                sps.lastSeen = currentMillis;
                sps.is_online = true;
                portEXIT_CRITICAL(&ble_mux);
            }

            // TB2 Decoder (ThermoBeacon 2)
            if (addr == "f0:f1:00:00:06:19" && len >= 19) {
                portENTER_CRITICAL(&ble_mux);
                const uint8_t* sensorBase = payload + 10; 
                tb2.temp = parseValue(sensorBase, 0, 16.0);
                tb2.humid = parseValue(sensorBase, 2, 16.0);
                tb2.packet = sensorBase[8];
                tb2.lastSeen = currentMillis;
                tb2.is_online = true;
                portEXIT_CRITICAL(&ble_mux);
            }
        }
    }
};

namespace BLEScanner {
    void init() {
        pBLEScan = BLEDevice::getScan(); 
        pBLEScan->setAdvertisedDeviceCallbacks(new MyScannerCallbacks(), true);
        
        // REPARATUR: ZURÜCK AUF ACTIVE SCAN FÜR DEN INKBIRD
        pBLEScan->setActiveScan(true); 
        pBLEScan->setInterval(500);    
        pBLEScan->setWindow(250);       
    }

    void update() {
        unsigned long currentMillis = millis();

        // 1. Watchdog
        if (currentMillis - sps.lastSeen > SENSOR_WATCHDOG_MS) sps.is_online = false;
        if (currentMillis - tb2.lastSeen > SENSOR_WATCHDOG_MS) tb2.is_online = false;

        // 2. Scan Intervall (Non-blocking)
        if (currentMillis - lastScanTime >= SCAN_INTERVAL || lastScanTime == 0) {
            lastScanTime = currentMillis;
            
            // 'nullptr' als zweiter Parameter, da wir Callbacks oben registriert haben.
            // 'false' am Ende bedeutet: Der Webserver läuft einfach weiter!
            if (!pBLEScan->isScanning()) {
                pBLEScan->start(SCAN_TIME, nullptr, false);
            }
        }
    }

    void get_status(JsonObject& obj) {
        JsonObject ble = obj.createNestedObject("ble_sensors");
        
        JsonObject j_sps = ble.createNestedObject("sps");
        j_sps["ble_temp_sps"] = sps.is_online ? sps.temp : -256.0;
        j_sps["ble_humid_sps"] = sps.is_online ? sps.humid : -256.0;
        j_sps["online"] = sps.is_online;
        j_sps["p"] = sps.packet;

        JsonObject j_tb2 = ble.createNestedObject("tb2");
        j_tb2["ble_temp_tb2"] = tb2.is_online ? tb2.temp : -256.0;
        j_tb2["ble_humid_tb2"] = tb2.is_online ? tb2.humid : -256.0;
        j_tb2["online"] = tb2.is_online;
        j_tb2["p"] = tb2.packet;
    }
}