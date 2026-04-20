#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>

// KEIN Mutex hier definieren!
// KEIN freertos include nötig!

namespace BLEScanner {
    void init();
    void update();
    void get_status(JsonObject& obj);
}