#include "sensor.h"
#include "config.h"
#include "hardware_init.h"
// Instanzen definieren (WICHTIG!)
Adafruit_SHT31 sht31_ext = Adafruit_SHT31(&I2C_Sensor);
Adafruit_SHT31 sht31_int = Adafruit_SHT31(&I2C_RTC);
float lastValidTempExt = -256.0;
float lastValidHumExt = -256.0;
unsigned long lastExternalSuccessUpdate = 0; 
const unsigned long SENSOR_TIMEOUT = 1000; // 1 Sekunde Dämpfung
bool externalSensorFound = false;
bool internalSensorFound = false;
extern bool externalSensorFound;


float getTempExt() {
    if (!externalSensorFound) return -256.0;

    float t = sht31_ext.readTemperature();

    if (!isnan(t) && t != -256.0) {
        // Alles okay, Zeitstempel und Wert merken
        lastValidTempExt = t;
        lastExternalSuccessUpdate = millis();
        return t;
    } else {
        // Fehler! Prüfen, ob wir noch innerhalb der 1s Toleranz sind
        if (millis() - lastExternalSuccessUpdate < SENSOR_TIMEOUT) {
            return lastValidTempExt; // "Lüge" und gib alten Wert aus
        } else {
            return -256.0; // Timeout abgelaufen, jetzt Fehler zeigen
        }
    }
}

float getExternalHumidity() {
    float h = sht31_ext.readHumidity();

    // Versuch 1: Normaler Read
    if (!isnan(h)) {
        lastValidHumExt = h;
        lastExternalSuccessUpdate = millis(); // Teilt sich den Timer mit Temp
        return h;
    }

    // Versuch 2: Kurze interne Wiederholung (hast du schon drin)
    for (int i = 0; i < 2; i++) {
        delay(20);
        h = sht31_ext.readHumidity();
        if (!isnan(h)) {
            lastValidHumExt = h;
            lastExternalSuccessUpdate = millis();
            return h;
        }
    }

    // Wenn hier gelandet -> Hardware-Fehler!
    Serial.println("I2C FAIL -> RECOVER ATTEMPT");
    recoverI2C(I2C_Sensor, I2C_SDA, I2C_SCL);
    sht31_ext.begin(0x44);

    // Watchdog-Check: Bevor wir -256 schicken, prüfen wir die Zeit
    if (millis() - lastExternalSuccessUpdate < SENSOR_TIMEOUT) {
        return lastValidHumExt; // Gib den letzten guten Wert zurück
    }

    return -256.0;
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
