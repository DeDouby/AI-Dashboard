#include "hardware_init.h"
#include "sensor.h"
#include "config.h"
extern TwoWire I2C_Sensor;
extern TwoWire I2C_RTC;

#define LEDC_FREQ 5000
#define LEDC_TIMER_10_BIT 10




void recoverI2C() {
    // Falls ein Bus hängt, hier Reset-Logik (optional)
    I2C_RTC.begin(RTC_SDA, RTC_SCL, 100000);
}
void init_sensor_bus()
{
    I2C_Sensor.begin(I2C_SDA, I2C_SCL, 100000);
    I2C_Sensor.setTimeOut(50);
}

void scan_i2c_devices()
{
    Serial.printf("\n--- I2C SCAN GPIO %d / %d ---\n", I2C_SDA, I2C_SCL);

    byte error, address;
    int nDevices = 0;

    for (address = 1; address < 127; address++)
    {
        I2C_Sensor.beginTransmission(address);
        error = I2C_Sensor.endTransmission();

        if (error == 0)
        {
            Serial.print("Gerät gefunden: 0x");
            if (address < 16) Serial.print("0");
            Serial.println(address, HEX);
            nDevices++;
        }
    }

    if (nDevices == 0)
        Serial.println("Kein I2C Gerät gefunden.");
    else
        Serial.printf("Scan fertig: %d Geräte\n", nDevices);
}

void init_hardware() {
    pinMode(PIN_BAT, INPUT);

    // Sensor Bus starten
    I2C_Sensor.begin(I2C_SDA, I2C_SCL, 100000);
    
    // RTC Bus starten
    I2C_RTC.begin(RTC_SDA, RTC_SCL, 100000);

    Serial.println("I2C Busse initialisiert.");
}