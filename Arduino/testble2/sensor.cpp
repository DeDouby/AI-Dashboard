#include "sensor.h"
#include "config.h"

// Instanzen definieren (WICHTIG!)
Adafruit_SHT31 sht31_ext = Adafruit_SHT31(&I2C_Sensor);
Adafruit_SHT31 sht31_int = Adafruit_SHT31(&I2C_RTC);

bool externalSensorFound = false;
bool internalSensorFound = false;
extern bool externalSensorFound;
float getTempExt() {
    if (!externalSensorFound) return -256.0;
    float t = sht31_ext.readTemperature();
    return isnan(t) ? -256.0 : t;
}

float getExternalHumidity() {
    if (!externalSensorFound) return -256.0;
    
    float h = sht31_ext.readHumidity();
    
    // SPORADISCHER FEHLER-CHECK:
    // Wenn h ungültig ist, versuchen wir es nach einer kurzen Pause erneut.
    if (isnan(h)) {
        delay(50); // Gib dem Sensor Zeit zum Atmen
        h = sht31_ext.readHumidity();
    }
    
    // Wenn es immer noch NaN ist, versuchen wir einen Soft-Reset für den nächsten Cycle
    if (isnan(h)) {
        // Optional: sht31_ext.reset(); 
        return -256.0;
    }
    
    return h;
}

// Gleiches Spiel für Intern
float getInternalHumidity() {
    if (!internalSensorFound) return -256.0;
    
    float h = sht31_int.readHumidity();
    
    if (isnan(h)) {
        delay(50);
        h = sht31_int.readHumidity();
    }
    
    return isnan(h) ? -256.0 : h;
}

float getTempIn() {
    if (!internalSensorFound) return -256.0;
    float t = sht31_int.readTemperature();
    return isnan(t) ? -256.0 : t;
}


bool initInternalSensor()
{
    if (!sht31_int.begin(0x44)) {
        Serial.println("INT SHT31 NICHT gefunden!");
        return false;
    }

    Serial.println("INT SHT31 gefunden");
    return true;
}
bool initExternalSensor()
{
    if (!sht31_ext.begin(0x44)) {
        Serial.println("EXT SHT31 NICHT gefunden!");
        return false;
    }

    Serial.println("EXT SHT31 gefunden");
    return true;
}
