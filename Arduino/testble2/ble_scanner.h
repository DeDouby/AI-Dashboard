#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>

namespace BLEScanner {
    void init();
    void update();

    void restart();
    bool isScanning();

    void get_status(JsonObject& obj);

    // ✅ HINZUFÜGEN:
    float get_sps_temp();
    float get_sps_hum();
    bool  is_sps_online();
}