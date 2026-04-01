#ifndef UI_HELPER_H
#define UI_HELPER_H
#include <lvgl.h>

// --- Bestehende Tiles ---
extern lv_obj_t * tileview;
extern lv_obj_t * tile_main;
extern lv_obj_t * tile_external;
extern lv_obj_t * tile_about;
extern lv_obj_t * tile_setup;
extern lv_obj_t * tile_info;
extern lv_obj_t * tile_vpd;
extern lv_obj_t * tile_fan;

// --- Neue About-Objekte ---
extern lv_obj_t * ui_about_cont;
extern lv_obj_t * ui_about_info;

// --- Bestehende Labels ---
extern lv_obj_t * ui_temp_label;
extern lv_obj_t * ui_humid_label;
extern lv_obj_t * ui_battery_label;
extern lv_obj_t * ui_brightness_label;
extern lv_obj_t * ui_chart_temp_label;
extern lv_obj_t * ui_fan_speed_label;
extern lv_obj_t * ui_vpd_label;
extern lv_obj_t * ui_vpd_ext_label;
extern lv_obj_t * ui_leaf_vpd_label;
extern lv_obj_t * ui_main_vpd_label;
extern lv_obj_t * ui_vpd_int_screen_label;
extern lv_obj_t * ui_main_humid_label;

// --- DAS FEHLENDE LABEL FÜR DIE UHRZEIT ---
extern lv_obj_t * ui_time_label; 

// --- Funktionen ---
void setup_ui();
void add_bg(lv_obj_t * tile, const void * img_src);

#endif