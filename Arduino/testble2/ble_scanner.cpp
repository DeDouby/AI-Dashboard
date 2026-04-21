#include "ble_scanner.h"
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <string>          // Für std::string

portMUX_TYPE ble_mux = portMUX_INITIALIZER_UNLOCKED;

// Feste Adressen (keine String-Vergleiche mehr im Hotpath)
static const BLEAddress INKBIRD_ADDR("49:25:08:23:07:21");
static const BLEAddress TB2_ADDR("f0:f1:00:00:06:19");

const uint32_t SCAN_TIME_MS      = 5000;   // Scan-Dauer
const uint32_t SCAN_INTERVAL_MS  = 6000;   // Alle 6 Sekunden starten
const uint32_t SENSOR_WATCHDOG_MS = 60000;

BLEScan* pBLEScan = nullptr;

struct SensorData {
    float temp = -256.0f;
    float humid = -256.0f;
    int packet = -1;
    unsigned long lastSeen = 0;
    bool is_online = false;
};

static SensorData sps;   // Inkbird
static SensorData tb2;   // ThermoBeacon

float parseValue(const uint8_t* data, int offset, float scale) {
    int16_t raw = data[offset] | (data[offset + 1] << 8);
    return (float)raw / scale;
}

// Callback – optimiert und heap-freundlich
class MyScannerCallbacks : public BLEAdvertisedDeviceCallbacks {
    void onResult(BLEAdvertisedDevice device) {
        if (!device.haveManufacturerData()) return;

        const BLEAddress& addr = device.getAddress();
        unsigned long currentMillis = millis();

        // Manufacturer Data nur bei Treffer holen
        if (addr.equals(INKBIRD_ADDR)) {
            String mData = device.getManufacturerData();   // Arduino String
            size_t len = mData.length();
            if (len < 7) return;

            uint8_t payload[32];
            memcpy(payload, mData.c_str(), len);   // .c_str() ist sicher hier

            portENTER_CRITICAL(&ble_mux);
            sps.temp = parseValue(payload, 0, 100.0f);
            sps.humid = parseValue(payload, 2, 100.0f);
            sps.packet = payload[6];
            sps.lastSeen = currentMillis;
            sps.is_online = true;
            portEXIT_CRITICAL(&ble_mux);
        }
        else if (addr.equals(TB2_ADDR)) {
            String mData = device.getManufacturerData();
            size_t len = mData.length();
            if (len < 19) return;

            uint8_t payload[32];
            memcpy(payload, mData.c_str(), len);

            portENTER_CRITICAL(&ble_mux);
            const uint8_t* sensorBase = payload + 10;
            tb2.temp = parseValue(sensorBase, 0, 16.0f);
            tb2.humid = parseValue(sensorBase, 2, 16.0f);
            tb2.packet = sensorBase[8];
            tb2.lastSeen = currentMillis;
            tb2.is_online = true;
            portEXIT_CRITICAL(&ble_mux);
        }
    }
};

namespace BLEScanner {
    void init() {
        pBLEScan = BLEDevice::getScan();
        pBLEScan->setAdvertisedDeviceCallbacks(new MyScannerCallbacks(), true);

        pBLEScan->setActiveScan(true);
        pBLEScan->setInterval(500);
        pBLEScan->setWindow(250);
    }
    void restart() {
        if (pBLEScan) {
            pBLEScan->stop();
            pBLEScan->clearResults();
            Serial.println("[BLEScanner] Restarted BLE Scan");
        }
    }

    bool isScanning() {
        return pBLEScan ? pBLEScan->isScanning() : false;
    }
    void update() {
        static uint32_t lastScanTime = 0;
        unsigned long currentMillis = millis();

        // Watchdog
        if (currentMillis - sps.lastSeen > SENSOR_WATCHDOG_MS) sps.is_online = false;
        if (currentMillis - tb2.lastSeen > SENSOR_WATCHDOG_MS) tb2.is_online = false;

        // Sparsamer Scan
        if (currentMillis - lastScanTime >= SCAN_INTERVAL_MS || lastScanTime == 0) {
            lastScanTime = currentMillis;

            if (!pBLEScan->isScanning()) {
                pBLEScan->start(SCAN_TIME_MS / 1000, nullptr, false);
                pBLEScan->clearResults();        // Wichtig gegen Fragmentierung
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