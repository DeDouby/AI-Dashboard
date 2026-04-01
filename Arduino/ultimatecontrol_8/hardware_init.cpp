#include "hardware_init.h"
#include "display_config.h"
#include "sensor.h"
#include <Arduino_GFX_Library.h>

extern TwoWire I2C_Sensor;

#define LEDC_FREQ 5000
#define LEDC_TIMER_10_BIT 10
#define GFX_BL 46
#define BAT_PIN 12

void init_display()
{
    gfx->begin();
    lcd_reg_init();
    gfx->setRotation(ROTATION);
}

void init_touch()
{
    Wire.begin(Touch_I2C_SDA, Touch_I2C_SCL);
    bsp_touch_init(&Wire, Touch_RST, Touch_INT, ROTATION, screenWidth, screenHeight);
}

void init_backlight()
{
    ledcAttach(GFX_BL, LEDC_FREQ, LEDC_TIMER_10_BIT);

    extern int global_brightness_percent;

    uint32_t duty = (1023 * global_brightness_percent) / 100;
    ledcWrite(GFX_BL, duty);
}

void init_sensor_bus()
{
    I2C_Sensor.begin(2, 3, 100000);
    I2C_Sensor.setTimeOut(50);
}

void scan_i2c_devices()
{
    Serial.println("\n--- I2C SCAN GPIO 2 / 3 ---");

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

void init_hardware()
{
    pinMode(LCD_RST, OUTPUT);
    pinMode(Touch_RST, OUTPUT);
    pinMode(Touch_INT, INPUT);
    pinMode(BAT_PIN, INPUT);

    digitalWrite(LCD_RST, 0);
    digitalWrite(Touch_RST, 0);
    delay(50);
    digitalWrite(LCD_RST, 1);
    digitalWrite(Touch_RST, 1);
    delay(150);

    init_touch();
    init_display();
    init_backlight();
    init_sensor_bus();
    scan_i2c_devices();
}