#include "sensor.h"
#include "config.h"

float getTempIn()
{
    // Der NTC-Sensor wurde entfernt. 
    // Wir geben hier einfach einen festen Standardwert zurück.
    float fixTemp = 25.0; 
    
    return fixTemp;
}
bool initExternalSensor()
{
    I2C_Sensor.begin(I2C_SDA, I2C_SCL, 100000);
    I2C_Sensor.setTimeOut(50);

    sht31.begin(0x44);

    return true;
}

float getTempExt() {
    float t = sht31.readTemperature();
    if (isnan(t)) return -256.0; // Geändert von -0.5
    return t;
}

float getExternalHumidity() {
    float h = sht31.readHumidity();
    if (isnan(h)) return -256.0; // Geändert von -0.5
    return h;
}

