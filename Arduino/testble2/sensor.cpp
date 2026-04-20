#include "sensor.h"
#include "config.h"
extern bool externalSensorFound;
float getTempIn()
{
    // Der NTC-Sensor wurde entfernt. 
    // Wir geben hier einfach einen festen Standardwert zurück.
    float fixTemp = 25.0; 
    
    return fixTemp;
}
bool initExternalSensor()
{
    if (!sht31.begin(0x44)) {
        Serial.println("SHT31 nicht erreichbar!");
        return false;
    }

    Serial.println("SHT31 gefunden!");
    return true;
}

float getTempExt() {
    if (!externalSensorFound) return -256.0;   // ✅ WICHTIG

    float t = sht31.readTemperature();
    if (isnan(t)) return -256.0;
    return t;
}

float getExternalHumidity() {
    if (!externalSensorFound) return -256.0;

    float h = sht31.readHumidity();
    if (isnan(h)) return -256.0;
    return h;
}