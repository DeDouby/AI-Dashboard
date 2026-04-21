#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>

// KEIN Mutex hier definieren!
// KEIN freertos include nötig!

namespace BLEScanner {
    void init();
    void update();
    
    void restart();        // ← NEU: Für periodischen Neustart
    bool isScanning();     // Optional, falls du es brauchst
    void get_status(JsonObject& obj);
}