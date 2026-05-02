#include "hardware_init.h"
#include "sensor.h"
#include "config.h"
extern TwoWire I2C_Sensor;
extern TwoWire I2C_RTC;

#define LEDC_FREQ 5000
#define LEDC_TIMER_10_BIT 10



void recoverI2C(TwoWire &bus, int sda, int scl) {
    bus.end();
    delay(10);
    bus.begin(sda, scl, 50000);
    delay(10);
}



void init_sensor_bus()
{
    // Wir nutzen deine Config-Pins 4 und 5
    I2C_Sensor.end(); 
    delay(50); 
    
    // Initialisierung mit deinen Werten aus der config.h
    I2C_Sensor.begin(I2C_SDA, I2C_SCL, 50000);
    
    // Timeout auf 20ms, damit der Bus bei Fehlern nicht hängen bleibt
    I2C_Sensor.setTimeOut(20);
    
    Serial.println("Sensor-Bus (Extern) mit Pins 4/5 gestartet.");
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
    I2C_Sensor.begin(I2C_SDA, I2C_SCL, 50000);
    
    // RTC Bus starten
    I2C_RTC.begin(RTC_SDA, RTC_SCL, 100000);

    Serial.println("I2C Busse initialisiert.");
}