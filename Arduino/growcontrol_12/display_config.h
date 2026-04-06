#ifndef DISPLAY_CONFIG_H
#define DISPLAY_CONFIG_H

#include "esp_lcd_touch_axs5106l.h"
#include <Arduino_GFX_Library.h>
#include <Wire.h>

#define LV_CONF_INCLUDE_SIMPLE
#include <lvgl.h>

// --- PINS ---
#define Touch_I2C_SDA 42
#define Touch_I2C_SCL 41
#define Touch_RST     47
#define Touch_INT     48
#define GFX_BL        46
#define LCD_RST       40
#define ROTATION      1

// --- DISPLAY OBJEKTE ---
extern Arduino_DataBus *bus;
extern Arduino_GFX *gfx;

// --- SCREEN ---
extern const uint32_t screenWidth;
extern const uint32_t screenHeight;

// --- FUNKTIONEN ---
void touchpad_read_cb(lv_indev_drv_t *indev_drv, lv_indev_data_t *data);
void lcd_reg_init(void);
void my_disp_flush(lv_disp_drv_t *disp, const lv_area_t *area, lv_color_t *color_p);
void setup_lvgl();

#endif