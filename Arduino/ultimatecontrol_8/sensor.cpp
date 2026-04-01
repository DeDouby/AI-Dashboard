#include "sensor.h"

float getTempIn()
{
    // --- 1. OVERSAMPLING (Gegen das Zucken) ---
    uint32_t adcSum = 0;
    const int numSamples = 32; // Wir messen 32x schnell hintereinander

    for(int i = 0; i < numSamples; i++) {
        adcSum += analogRead(SENSOR_PIN);
        delayMicroseconds(50); // Ganz kurze Beruhigungspause für den ADC
    }

    float adcValue = (float)adcSum / numSamples; // Der saubere Durchschnitt

    // --- 2. SICHERHEITS-CHECK ---
    if (adcValue < 10) return -256.0; // Sensor nicht verbunden (Pseudo-Wert)
    if (adcValue > 4085) return -256.0; // Kurzschluss (Pseudo-Wert)

    // --- 3. DIE BERECHNUNG (Wie gehabt, aber mit Durchschnitt) ---
    float resistance = (float)30000 * (4095.0 / adcValue - 1.0);
    float steinhart = resistance / 30000;

    steinhart = log(steinhart);
    steinhart /= 3950;
    steinhart += 1.0 / (35 + 273.15);
    steinhart = 1.0 / steinhart;

    return steinhart - 273.15;
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

