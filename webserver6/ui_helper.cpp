#include "ui_helper.h"
#include <Arduino.h> 
#include "fan.h"
#define GFX_BL 46  

// WICHTIG: Sagt dem Compiler, dass diese Variablen in der main.cpp existieren
extern uint32_t screen_timeout;
extern int global_brightness_percent;

// Hier werden die UI-Objekte definiert
lv_obj_t * tileview;
lv_obj_t * ui_temp_label;
lv_obj_t * ui_humid_label;
lv_obj_t * ui_battery_label;
lv_obj_t * temp_chart;
lv_obj_t * ui_min_label;
lv_obj_t * ui_max_label;
lv_obj_t * ui_trend_icon;
lv_obj_t * ui_brightness_label;
lv_obj_t * ui_chart_temp_label;
lv_obj_t * tile_main;
lv_obj_t * tile_setup;
lv_obj_t * tile_info;
lv_obj_t * tile_vpd;
lv_obj_t * ui_vpd_label;
lv_obj_t * ui_leaf_vpd_label;
lv_obj_t * ui_chart_only_temp_label; 
lv_obj_t * ui_vpd_ext_label;  
lv_obj_t * ui_main_vpd_label; // <--- DIESE ZEILE HIER EINFÜGEN!
lv_obj_t * ui_vpd_int_screen_label; // <--- DIESE ZEILE MUSS HIER REIN!
lv_obj_t * ui_about_cont;
lv_obj_t * ui_about_info;
lv_obj_t * btn_nat;
lv_obj_t * btn_chao;
lv_obj_t * tile_external; 
lv_obj_t * tile_about;
lv_chart_series_t * ui_temp_series;
lv_chart_series_t * ui_humid_series;
lv_chart_series_t * ui_vpd_series;
lv_obj_t * tile_fan;           // <--- HIER EINFÜGEN
lv_obj_t * ui_fan_speed_label;  // <---
lv_obj_t * ui_main_humid_label;  // <--- DIESE ZEILE HIER EINFÜGEN
static lv_obj_t * b30;
static lv_obj_t * b1m;
static lv_obj_t * bon;
// Zugriff auf das Bild
LV_IMG_DECLARE(bild_1); 
LV_IMG_DECLARE(bild_2); // <--- Auch hier hinzufügen

LV_IMG_DECLARE(bild_3); // <--- Die neue Nummer 3
LV_IMG_DECLARE(bild_4); // <--- DAS NEUE OSTEREI

// ---------- CALLBACKS ----------
void btn_30s_cb(lv_event_t * e) { 
    screen_timeout = 30000; 
    lv_obj_clear_state(b1m, LV_STATE_CHECKED);
    lv_obj_clear_state(bon, LV_STATE_CHECKED);
    lv_obj_add_state(b30, LV_STATE_CHECKED);
}

void btn_1m_cb(lv_event_t * e)  { 
    screen_timeout = 60000; 
    lv_obj_clear_state(b30, LV_STATE_CHECKED);
    lv_obj_clear_state(bon, LV_STATE_CHECKED);
    lv_obj_add_state(b1m, LV_STATE_CHECKED);
}

void btn_on_cb(lv_event_t * e)  { 
    screen_timeout = 0xFFFFFFFF; 
    lv_obj_clear_state(b30, LV_STATE_CHECKED);
    lv_obj_clear_state(b1m, LV_STATE_CHECKED);
    lv_obj_add_state(bon, LV_STATE_CHECKED);
}
// ---------- OPTIMIERTER HINTERGRUND-HELPER ----------
// Wir fügen einen Parameter "img_src" hinzu
void add_bg(lv_obj_t * tile, const void * img_src) {
    lv_obj_t * bg = lv_img_create(tile);
    lv_img_set_src(bg, img_src); // Nutzt jetzt das übergebene Bild
    lv_obj_center(bg);
    lv_obj_add_flag(bg, LV_OBJ_FLAG_EVENT_BUBBLE); 
    lv_obj_clear_flag(bg, LV_OBJ_FLAG_CLICKABLE);  
    lv_obj_move_to_index(bg, 0); 
}



void slider_event_cb(lv_event_t * e) {
    lv_obj_t * slider = lv_event_get_target(e);
    global_brightness_percent = lv_slider_get_value(slider);
    uint32_t duty = (1023 * global_brightness_percent) / 100;
    ledcWrite(GFX_BL, duty);
    lv_label_set_text_fmt(ui_brightness_label, "Brightness %d %%", global_brightness_percent);
}


// ---------- UI SETUP ----------
void setup_ui() {
    lv_obj_t * main_screen = lv_scr_act();
    lv_obj_set_style_bg_color(main_screen, lv_color_hex(0x000000), 0);

    // Tileview Initialisierung (NUR EINMAL!)
    tileview = lv_tileview_create(main_screen);
    lv_obj_set_size(tileview, 320, 172);
    lv_obj_center(tileview);
    lv_obj_set_scroll_dir(tileview, LV_DIR_ALL);
    
     // --- Tiles hinzufügen & Wege definieren ---
    tile_main     = lv_tileview_add_tile(tileview, 1, 1, LV_DIR_ALL);
    tile_setup    = lv_tileview_add_tile(tileview, 1, 0, LV_DIR_BOTTOM | LV_DIR_RIGHT); 
    tile_fan      = lv_tileview_add_tile(tileview, 2, 0, LV_DIR_LEFT | LV_DIR_BOTTOM); 
    tile_about    = lv_tileview_add_tile(tileview, 0, 1, LV_DIR_RIGHT); // Klar benannt!
    tile_external = lv_tileview_add_tile(tileview, 2, 1, LV_DIR_LEFT | LV_DIR_RIGHT | LV_DIR_TOP);  
    tile_vpd      = lv_tileview_add_tile(tileview, 3, 1, LV_DIR_LEFT); 
    tile_info     = lv_tileview_add_tile(tileview, 1, 2, LV_DIR_TOP);
    
    // --- HIER kannst du jetzt gezielt die BGs ändern! ---
    add_bg(tile_main,     &bild_3); 
    add_bg(tile_about,    &bild_2); // About bekommt jetzt Bild 2 statt Bild 1
    add_bg(tile_external, &bild_2); 
    add_bg(tile_vpd,      &bild_3); 
    add_bg(tile_setup,    &bild_2); 
    add_bg(tile_info,     &bild_1); 
    add_bg(tile_fan,      &bild_1);

    lv_obj_set_tile_id(tileview, 1, 1, LV_ANIM_OFF);


// ================= MAIN TILE (GLOSSY BOX LAYOUT) =================
    
    // 1. Die Glossy Box (Zentraler Container, kein Rand)
    lv_obj_t * main_glossy_box = lv_obj_create(tile_main);
    lv_obj_set_size(main_glossy_box, 300, 150); 
    lv_obj_align(main_glossy_box, LV_ALIGN_CENTER, 0, 0);
    lv_obj_set_style_bg_color(main_glossy_box, lv_color_hex(0x000000), 0);
    lv_obj_set_style_bg_opa(main_glossy_box, LV_OPA_60, 0); 
    lv_obj_set_style_border_color(main_glossy_box, lv_color_hex(0x00FF88), 0);

    lv_obj_set_style_border_width(main_glossy_box, 0, 0); 
    lv_obj_set_style_radius(main_glossy_box, 12, 0);
    lv_obj_clear_flag(main_glossy_box, LV_OBJ_FLAG_SCROLLABLE);
    
    // --- MITTLERE SEKTION (Temp & Humid) ---
    
    // 3. TEMPERATURE (Links)
    ui_temp_label = lv_label_create(main_glossy_box);
    lv_obj_set_style_text_font(ui_temp_label, &lv_font_montserrat_32, 0);
    lv_obj_set_style_text_color(ui_temp_label, lv_color_hex(0x00FFFF), 0);
    lv_obj_align(ui_temp_label, LV_ALIGN_CENTER, -70, -25); 
    lv_label_set_text(ui_temp_label, "--.- °C");
    
    lv_obj_t * t_main_label = lv_label_create(main_glossy_box);
    lv_label_set_text(t_main_label, "INT TEMP");
    lv_obj_set_style_text_font(t_main_label, &lv_font_montserrat_16, 0);
    lv_obj_set_style_text_color(t_main_label, lv_color_hex(0xEEEEEE), 0);
    lv_obj_align_to(t_main_label, ui_temp_label, LV_ALIGN_OUT_TOP_MID, 0, -5);
    
    // 4. HUMIDITY (Rechts)
    ui_main_humid_label = lv_label_create(main_glossy_box); 
    lv_obj_set_style_text_font(ui_main_humid_label, &lv_font_montserrat_32, 0);
    lv_obj_set_style_text_color(ui_main_humid_label, lv_color_hex(0x00FF88), 0);
    lv_obj_align(ui_main_humid_label, LV_ALIGN_CENTER, 70, -25);
    lv_label_set_text(ui_main_humid_label, "40.0 %"); 
    
    lv_obj_t * h_main_label = lv_label_create(main_glossy_box);
    lv_label_set_text(h_main_label, "INT HUM");
    lv_obj_set_style_text_font(h_main_label, &lv_font_montserrat_16, 0);
    lv_obj_set_style_text_color(h_main_label, lv_color_hex(0xEEEEEE), 0);
    lv_obj_align_to(h_main_label, ui_main_humid_label, LV_ALIGN_OUT_TOP_MID, 0, -5);
    
    // --- UNTERE SEKTION (VPD) ---
    
    // 5. VPD (Zentriert unten)
    ui_main_vpd_label = lv_label_create(main_glossy_box);
    lv_obj_set_style_text_font(ui_main_vpd_label, &lv_font_montserrat_40, 0); // 36 statt 42 für Box-Proportion
    lv_obj_set_style_text_color(ui_main_vpd_label, lv_color_hex(0xFFCC88), 0);
    lv_obj_align(ui_main_vpd_label, LV_ALIGN_BOTTOM_MID, 0, 5); 
    lv_label_set_text(ui_main_vpd_label, "-.--");
    
    lv_obj_t * v_main_label = lv_label_create(main_glossy_box);
    lv_label_set_text(v_main_label, "INT VPD");
    lv_obj_set_style_text_font(v_main_label, &lv_font_montserrat_16, 0);
    lv_obj_set_style_text_color(v_main_label, lv_color_hex(0xEEEEEE), 0);
    lv_obj_align_to(v_main_label, ui_main_vpd_label, LV_ALIGN_OUT_TOP_MID, 0, -5);

    // ================= EXTERNAL SENSOR TILE (GLOSSY BOX LAYOUT) =================
    
    // 1. Die Glossy Box (Zentraler Container, kein Rand)
    lv_obj_t * external_glossy_box = lv_obj_create(tile_external);
    lv_obj_set_size(external_glossy_box, 300, 150); 
    lv_obj_align(external_glossy_box, LV_ALIGN_CENTER, 0, 0);
    lv_obj_set_style_bg_color(external_glossy_box, lv_color_hex(0x000000), 0);
    lv_obj_set_style_bg_opa(external_glossy_box, LV_OPA_60, 0); 
    lv_obj_set_style_border_width(external_glossy_box, 0, 0); 
    lv_obj_set_style_radius(external_glossy_box, 12, 0);
    lv_obj_clear_flag(external_glossy_box, LV_OBJ_FLAG_SCROLLABLE);
    
    // --- MITTLERE SEKTION (Temp & Humid) ---
    
    // 2. TEMPERATURE (Links)
    ui_chart_temp_label = lv_label_create(external_glossy_box);
    lv_obj_set_style_text_font(ui_chart_temp_label, &lv_font_montserrat_32, 0);
    lv_obj_set_style_text_color(ui_chart_temp_label, lv_color_hex(0x00FFFF), 0);
    lv_obj_align(ui_chart_temp_label, LV_ALIGN_CENTER, -70, -25); 
    lv_label_set_text(ui_chart_temp_label, "--.- °C");
    
    lv_obj_t * t_label = lv_label_create(external_glossy_box);
    lv_label_set_text(t_label, "EXT TEMP");
    lv_obj_set_style_text_font(t_label, &lv_font_montserrat_16, 0);
    lv_obj_set_style_text_color(t_label, lv_color_hex(0xEEEEEE), 0);
    lv_obj_align_to(t_label, ui_chart_temp_label, LV_ALIGN_OUT_TOP_MID, 0, -5);
    
    // 3. HUMIDITY (Rechts)
    ui_humid_label = lv_label_create(external_glossy_box); 
    lv_obj_set_style_text_font(ui_humid_label, &lv_font_montserrat_32, 0);
    lv_obj_set_style_text_color(ui_humid_label, lv_color_hex(0x00FF88), 0);
    lv_obj_align(ui_humid_label, LV_ALIGN_CENTER, 70, -25);
    lv_label_set_text(ui_humid_label, "--.- %"); 
    
    lv_obj_t * h_label = lv_label_create(external_glossy_box);
    lv_label_set_text(h_label, "EXT HUM");
    lv_obj_set_style_text_font(h_label, &lv_font_montserrat_16, 0);
    lv_obj_set_style_text_color(h_label, lv_color_hex(0xEEEEEE), 0);
    lv_obj_align_to(h_label, ui_humid_label, LV_ALIGN_OUT_TOP_MID, 0, -5);
    
    // --- UNTERE SEKTION (VPD) ---
    
    // 4. VPD (Zentriert unten)
    ui_vpd_label = lv_label_create(external_glossy_box);
    lv_obj_set_style_text_font(ui_vpd_label, &lv_font_montserrat_40, 0); 
    lv_obj_set_style_text_color(ui_vpd_label, lv_color_hex(0xFFCC88), 0);
    lv_obj_align(ui_vpd_label, LV_ALIGN_BOTTOM_MID, 0, 5); 
    lv_label_set_text(ui_vpd_label, "-.--");
    
    lv_obj_t * v_label = lv_label_create(external_glossy_box);
    lv_label_set_text(v_label, "EXT VPD");
    lv_obj_set_style_text_font(v_label, &lv_font_montserrat_16, 0);
    lv_obj_set_style_text_color(v_label, lv_color_hex(0xEEEEEE), 0);
    lv_obj_align_to(v_label, ui_vpd_label, LV_ALIGN_OUT_TOP_MID, 0, -5);

    
// ================= ABOUT TILE (The Project's Identity) =================
// ================= ABOUT TILE (The Project's Identity + Easter Egg) =================
    
    // 1. Ein schicker Rahmen/Container für die Info
    lv_obj_t * about_cont = lv_obj_create(tile_about);
    lv_obj_set_size(about_cont, 280, 135);
    lv_obj_align(about_cont, LV_ALIGN_CENTER, 0, 0);
    lv_obj_set_style_bg_color(about_cont, lv_color_hex(0x000000), 0);
    lv_obj_set_style_bg_opa(about_cont, LV_OPA_60, 0); 
    lv_obj_set_style_border_color(about_cont, lv_color_hex(0x00FF88), 0);
    lv_obj_set_style_border_width(about_cont, 2, 0);
    lv_obj_set_style_radius(about_cont, 12, 0);
    
    // --- NEU: Klickbar machen für das Easter Egg ---
    lv_obj_add_flag(about_cont, LV_OBJ_FLAG_CLICKABLE); 
    lv_obj_add_event_cb(about_cont, [](lv_event_t * e) {
        static uint8_t clicks = 0;
        static uint32_t last_time = 0;
        
        // Reset nach 2 Sekunden Inaktivität
        if(millis() - last_time > 2000) clicks = 0;
        last_time = millis();
        clicks++;
    
        if(clicks >= 7) {
            clicks = 0; // Reset
            // Bild 4 (Easter Egg) über den ganzen Screen legen
            lv_obj_t * egg = lv_img_create(lv_scr_act());
            lv_img_set_src(egg, &bild_4);
            lv_obj_center(egg);
            lv_obj_add_flag(egg, LV_OBJ_FLAG_CLICKABLE);
            
            // Klick auf das Bild schließt es wieder
            lv_obj_add_event_cb(egg, [](lv_event_t * ev){
                lv_obj_del(lv_event_get_target(ev));
            }, LV_EVENT_CLICKED, NULL);
        }
    }, LV_EVENT_CLICKED, NULL);
    
    // 2. Projekt Name
    lv_obj_t * about_title = lv_label_create(about_cont);
    lv_label_set_text(about_title, "Living Sensor S3");
    lv_obj_set_style_text_font(about_title, &lv_font_montserrat_18, 0);
    lv_obj_set_style_text_color(about_title, lv_color_hex(0x00FFFF), 0);
    lv_obj_align(about_title, LV_ALIGN_TOP_MID, 0, 5);
    
    // 3. Trennlinie
    lv_obj_t * line = lv_line_create(about_cont);
    static lv_point_t line_points[] = { {0, 0}, {200, 0} };
    lv_line_set_points(line, line_points, 2);
    lv_obj_set_style_line_color(line, lv_color_hex(0x00FF88), 0);
    lv_obj_set_style_line_width(line, 1, 0);
    lv_obj_align(line, LV_ALIGN_TOP_MID, 0, 30);
    
    // 4. Die "Vorstellung"
    lv_obj_t * about_info_label = lv_label_create(about_cont);
    lv_label_set_long_mode(about_info_label, LV_LABEL_LONG_WRAP);
    lv_obj_set_width(about_info_label, 240);
    lv_label_set_text(about_info_label, 
        "Monitoring your plants.\n"
        "Hardware: ESP32-S3 | 1.47\" LCD");
    lv_obj_set_style_text_align(about_info_label, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_set_style_text_font(about_info_label, &lv_font_montserrat_14, 0);
    lv_obj_set_style_text_color(about_info_label, lv_color_hex(0xEEEEEE), 0);
    lv_obj_align(about_info_label, LV_ALIGN_TOP_MID, 0, 45);
    

    

// ================= SETUP DISPLAY TILE =================
    // 1. Titel & Brightness Label
    ui_brightness_label = lv_label_create(tile_setup);
    lv_label_set_text_fmt(ui_brightness_label, "Brightness: %d %%", global_brightness_percent);
    lv_obj_set_style_text_font(ui_brightness_label, &lv_font_montserrat_16, 0); // Feste Größe 16
    lv_obj_set_style_text_color(ui_brightness_label, lv_color_hex(0x00FF88), 0); // Farbe passend zum System
    lv_obj_align(ui_brightness_label, LV_ALIGN_TOP_MID, 0, 15);
    
    // 2. Brightness Slider
    lv_obj_t * slider = lv_slider_create(tile_setup);
    lv_obj_set_size(slider, 260, 15); // Etwas dicker für bessere Bedienung
    lv_obj_align(slider, LV_ALIGN_TOP_MID, 0, 45);
    lv_slider_set_value(slider, global_brightness_percent, LV_ANIM_OFF);
    lv_obj_add_event_cb(slider, slider_event_cb, LV_EVENT_VALUE_CHANGED, NULL);

    // Trennlinie oder Abstandshalter-Label
    lv_obj_t * timeout_label = lv_label_create(tile_setup);
    lv_label_set_text(timeout_label, "SCREEN TIMEOUT");
    lv_obj_set_style_text_font(timeout_label, &lv_font_montserrat_16, 0);
    lv_obj_set_style_text_color(timeout_label, lv_color_hex(0x00FF88), 0);
    lv_obj_align(timeout_label, LV_ALIGN_TOP_MID, 0, 85);

    // --- BUTTON GRUPPE ---
    // Button: 30s
    b30 = lv_btn_create(tile_setup); 
    lv_obj_set_size(b30, 85, 45); // Höher für bessere Haptik
    lv_obj_align(b30, LV_ALIGN_TOP_MID, -95, 115);
    lv_obj_add_flag(b30, LV_OBJ_FLAG_CHECKABLE); 
    lv_obj_add_event_cb(b30, btn_30s_cb, LV_EVENT_CLICKED, NULL);
    lv_obj_t * l30 = lv_label_create(b30);
    lv_label_set_text(l30, "30s");
    lv_obj_center(l30);

    // Button: 1m
    b1m = lv_btn_create(tile_setup);
    lv_obj_set_size(b1m, 85, 45);
    lv_obj_align(b1m, LV_ALIGN_TOP_MID, 0, 115);
    lv_obj_add_flag(b1m, LV_OBJ_FLAG_CHECKABLE);
    lv_obj_add_event_cb(b1m, btn_1m_cb, LV_EVENT_CLICKED, NULL);
    lv_obj_t * l1m = lv_label_create(b1m);
    lv_label_set_text(l1m, "1m");
    lv_obj_center(l1m);

    // Button: ON
    bon = lv_btn_create(tile_setup);
    lv_obj_set_size(bon, 85, 45);
    lv_obj_align(bon, LV_ALIGN_TOP_MID, 95, 115);
    lv_obj_add_flag(bon, LV_OBJ_FLAG_CHECKABLE);
    lv_obj_add_event_cb(bon, btn_on_cb, LV_EVENT_CLICKED, NULL);
    lv_obj_t * lon = lv_label_create(bon);
    lv_label_set_text(lon, "ALWAYS"); // "ALWAYS" statt "ON" ist klarer
    lv_obj_center(lon);

    // Initialen Zustand setzen
    lv_obj_add_state(b30, LV_STATE_CHECKED);

// --- FAN TILE ---
    tile_fan = lv_tileview_add_tile(tileview, 2, 0, LV_DIR_ALL); 
    
    lv_obj_t * fan_title = lv_label_create(tile_fan);
    lv_label_set_text(fan_title, "PWM FAN CONTROL (GPIO 4)");
    lv_obj_set_style_text_font(fan_title, &lv_font_montserrat_16, 0);
    lv_obj_set_style_text_color(fan_title, lv_color_hex(0x00FF88), 0);
    lv_obj_align(fan_title, LV_ALIGN_TOP_MID, 0, 10);
    
    // Speed & RPM Label
    ui_fan_speed_label = lv_label_create(tile_fan);
    lv_label_set_text(ui_fan_speed_label, "60 % | 0 RPM"); 
    lv_obj_set_style_text_color(ui_fan_speed_label, lv_color_hex(0x00FFFF), 0); 
    lv_obj_set_style_text_font(ui_fan_speed_label, &lv_font_montserrat_22, 0);
    lv_obj_align(ui_fan_speed_label, LV_ALIGN_CENTER, 0, -40);

    // --- 1. BUTTONS ERSTELLEN ---
    btn_nat = lv_btn_create(tile_fan);
    lv_obj_set_size(btn_nat, 110, 45);
    lv_obj_align(btn_nat, LV_ALIGN_BOTTOM_LEFT, 20, -15);
    lv_obj_add_flag(btn_nat, LV_OBJ_FLAG_CHECKABLE); 
    lv_obj_add_state(btn_nat, LV_STATE_CHECKED); // Start auf Natural

    lv_obj_t * lbl_nat = lv_label_create(btn_nat);
    lv_label_set_text(lbl_nat, "NATURAL");
    lv_obj_center(lbl_nat);

    btn_chao = lv_btn_create(tile_fan);
    lv_obj_set_size(btn_chao, 110, 45);
    lv_obj_align(btn_chao, LV_ALIGN_BOTTOM_RIGHT, -20, -15);
    lv_obj_add_flag(btn_chao, LV_OBJ_FLAG_CHECKABLE); 
    
    lv_obj_t * lbl_chao = lv_label_create(btn_chao);
    lv_label_set_text(lbl_chao, "CHAOTIC");
    lv_obj_center(lbl_chao);

    // --- 2. BUTTON CALLBACKS ---
    lv_obj_add_event_cb(btn_nat, [](lv_event_t * e) {
        lv_obj_t * obj = lv_event_get_target(e);
        if(lv_obj_has_state(obj, LV_STATE_CHECKED)) {
            fan_set_mode(FAN_MODE_NATURAL);
            lv_obj_clear_state(btn_chao, LV_STATE_CHECKED); 
        } else {
            fan_set_mode(FAN_MODE_MANUAL);
        }
    }, LV_EVENT_CLICKED, NULL);

    lv_obj_add_event_cb(btn_chao, [](lv_event_t * e) {
        lv_obj_t * obj = lv_event_get_target(e);
        if(lv_obj_has_state(obj, LV_STATE_CHECKED)) {
            fan_set_mode(FAN_MODE_CHAOTIC);
            lv_obj_clear_state(btn_nat, LV_STATE_CHECKED); 
        } else {
            fan_set_mode(FAN_MODE_MANUAL);
        }
    }, LV_EVENT_CLICKED, NULL);

    // --- 3. SLIDER (Keine Redeklaration mehr) ---
    lv_obj_t * fan_slider = lv_slider_create(tile_fan); // Hier wird er erstellt
    lv_obj_set_size(fan_slider, 240, 25);
    lv_obj_align(fan_slider, LV_ALIGN_CENTER, 0, 0);
    lv_slider_set_range(fan_slider, 0, 100);
    lv_slider_set_value(fan_slider, 60, LV_ANIM_OFF);

    lv_obj_add_event_cb(fan_slider, [](lv_event_t * e) {
        int val = lv_slider_get_value(lv_event_get_target(e));
        current_fan_speed = val; 
        lv_obj_clear_state(btn_nat, LV_STATE_CHECKED);
        lv_obj_clear_state(btn_chao, LV_STATE_CHECKED);
        fan_set_mode(FAN_MODE_MANUAL); 
        fan_set_speed(val); 
    }, LV_EVENT_VALUE_CHANGED, NULL);
    
// ================= INFO TILE BATT§ERY =================
    lv_obj_t * i_title = lv_label_create(tile_info);
    lv_label_set_text(i_title, "BATTERY STATUS");
    lv_obj_set_style_text_font(i_title, &lv_font_montserrat_16, 0);
    lv_obj_set_style_text_color(i_title, lv_color_hex(0x00FF88), 0);
    lv_obj_align(i_title, LV_ALIGN_TOP_LEFT, 20, 15);
    
    ui_battery_label = lv_label_create(tile_info);
    lv_obj_set_style_text_font(ui_battery_label, &lv_font_montserrat_48, 0);
    lv_obj_set_style_text_color(ui_battery_label, lv_color_hex(0x00FF88), 0);
    lv_obj_align(ui_battery_label, LV_ALIGN_CENTER, 0, 0); 
    
    lv_obj_t * i_hint = lv_label_create(tile_info);
    lv_label_set_text(i_hint, "Swipe up to return");
    lv_obj_set_style_text_color(i_hint, lv_color_hex(0xEEEEEE), 0);
    lv_obj_align(i_hint, LV_ALIGN_BOTTOM_MID, 0, -15);



// ================= VPD SCREEN (ext, LEAF, INTERNAL) =================
    
    // 1. Die Glossy Box (Zentraler Container ohne Rahmen)
    lv_obj_t * vpd_glossy_box = lv_obj_create(tile_vpd);
    lv_obj_set_size(vpd_glossy_box, 300, 130); // Fast volle Breite
    lv_obj_align(vpd_glossy_box, LV_ALIGN_CENTER, 0, 0);
    lv_obj_set_style_bg_color(vpd_glossy_box, lv_color_hex(0x000000), 0);
    lv_obj_set_style_bg_opa(vpd_glossy_box, LV_OPA_60, 0); 
    lv_obj_set_style_border_width(vpd_glossy_box, 0, 0); // KEIN grüner Rand
    lv_obj_set_style_radius(vpd_glossy_box, 12, 0);
    lv_obj_clear_flag(vpd_glossy_box, LV_OBJ_FLAG_SCROLLABLE); // Box soll nicht scrollen
    
    // --- ext VPD (LINKS) ---
    lv_obj_t * ext_header = lv_label_create(vpd_glossy_box); // Elternteil ist jetzt die Box
    lv_label_set_text(ext_header, "ext");
    lv_obj_set_style_text_font(ext_header, &lv_font_montserrat_16, 0);
    lv_obj_set_style_text_color(ext_header, lv_color_hex(0xEEEEEE), 0);
    lv_obj_align(ext_header, LV_ALIGN_CENTER, -95, -40);
    
    ui_vpd_ext_label = lv_label_create(vpd_glossy_box); 
    lv_obj_set_style_text_font(ui_vpd_ext_label, &lv_font_montserrat_36, 0); 
    lv_obj_set_style_text_color(ui_vpd_ext_label, lv_color_hex(0xFFCC88), 0); 
    lv_obj_align(ui_vpd_ext_label, LV_ALIGN_CENTER, -95, 0);
    
    lv_obj_t * ui_vpd_ext_unit = lv_label_create(vpd_glossy_box);
    lv_label_set_text(ui_vpd_ext_unit, "kPa");
    lv_obj_set_style_text_font(ui_vpd_ext_unit, &lv_font_montserrat_16, 0);
    lv_obj_set_style_text_color(ui_vpd_ext_unit, lv_color_hex(0xEEEEEE), 0);
    lv_obj_align_to(ui_vpd_ext_unit, ui_vpd_ext_label, LV_ALIGN_OUT_BOTTOM_MID, 0, 2);
    
    // --- LEAF VPD (MITTE) ---
    lv_obj_t * leaf_header = lv_label_create(vpd_glossy_box);
    lv_label_set_text(leaf_header, "LEAF");
    lv_obj_set_style_text_font(leaf_header, &lv_font_montserrat_16, 0);
    lv_obj_set_style_text_color(leaf_header, lv_color_hex(0xEEEEEE), 0);
    lv_obj_align(leaf_header, LV_ALIGN_CENTER, 0, -40);
    
    ui_leaf_vpd_label = lv_label_create(vpd_glossy_box); 
    lv_obj_set_style_text_font(ui_leaf_vpd_label, &lv_font_montserrat_36, 0); 
    lv_obj_set_style_text_color(ui_leaf_vpd_label, lv_color_hex(0x00FFFF), 0); 
    lv_obj_align(ui_leaf_vpd_label, LV_ALIGN_CENTER, 0, 0);
    
    lv_obj_t * ui_leaf_vpd_unit = lv_label_create(vpd_glossy_box);
    lv_label_set_text(ui_leaf_vpd_unit, "kPa");
    lv_obj_set_style_text_font(ui_leaf_vpd_unit, &lv_font_montserrat_16, 0);
    lv_obj_set_style_text_color(ui_leaf_vpd_unit, lv_color_hex(0xEEEEEE), 0);
    lv_obj_align_to(ui_leaf_vpd_unit, ui_leaf_vpd_label, LV_ALIGN_OUT_BOTTOM_MID, 0, 2);
    
    // --- INTERNAL VPD (RECHTS) ---
    lv_obj_t * int_header = lv_label_create(vpd_glossy_box);
    lv_label_set_text(int_header, "INTERNAL");
    lv_obj_set_style_text_font(int_header, &lv_font_montserrat_16, 0);
    lv_obj_set_style_text_color(int_header, lv_color_hex(0xEEEEEE), 0);
    lv_obj_align(int_header, LV_ALIGN_CENTER, 95, -40);
    
    ui_vpd_int_screen_label = lv_label_create(vpd_glossy_box); 
    lv_obj_set_style_text_font(ui_vpd_int_screen_label, &lv_font_montserrat_36, 0); 
    lv_obj_set_style_text_color(ui_vpd_int_screen_label, lv_color_hex(0xFF88AA), 0); 
    lv_obj_align(ui_vpd_int_screen_label, LV_ALIGN_CENTER, 95, 0);
    
    lv_obj_t * ui_vpd_int_unit = lv_label_create(vpd_glossy_box);
    lv_label_set_text(ui_vpd_int_unit, "kPa");
    lv_obj_set_style_text_font(ui_vpd_int_unit, &lv_font_montserrat_16, 0);
    lv_obj_set_style_text_color(ui_vpd_int_unit, lv_color_hex(0xEEEEEE), 0);
    lv_obj_align_to(ui_vpd_int_unit, ui_vpd_int_screen_label, LV_ALIGN_OUT_BOTTOM_MID, 0, 2);
    
    // Footer Text (Außerhalb der Box für mehr Raumtiefe)
    lv_obj_t * vpd_hint = lv_label_create(tile_vpd);
    lv_label_set_text(vpd_hint, "SHT31 ext | SHT31 -2C | NTC + 40%");
    lv_obj_set_style_text_font(vpd_hint, &lv_font_montserrat_16, 0); 
    lv_obj_set_style_text_color(vpd_hint, lv_color_hex(0xEEEEEE), 0); 
    lv_obj_align(vpd_hint, LV_ALIGN_BOTTOM_MID, 0, -5);
}