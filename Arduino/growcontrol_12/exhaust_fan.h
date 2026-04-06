
///////////////////////////////////////////////////////////////////////////////
// !!! ABSOLUTES GESETZ: DAS TARGET-REVISION-PRINZIP (C++ / ESP32) !!!
// -------------------------------------------------------------------------
// 1. HARDWARE FOLGT TARGET: Die Loop darf NIEMALS direkt auf UI-Inputs reagieren.
//    Sie vergleicht permanent: 'target_val' vs 'effective_val'.
//
// 2. REVISION-CONFIRMATION: Der ESP32 bestätigt eine Änderung NUR, indem er 
//    die empfangene 'rev' (Revision) im Status-Paket unverändert zurücksendet.
//
// 3. KEINE LÜGEN: Der Status 'Synced' (Grün in der App) darf NUR dann entstehen,
//    wenn 'esp32_rev' == 'ui_target_rev'.
//
// 4. ATOMARE UPDATES: Bei Empfang eines neuen Targets wird die 'rev' sofort 
//    gespeichert, aber der 'effective_val' zieht (ggf. über Rampen) stur nach.
//
// JEDE KI-ÄNDERUNG MUSS DIESE ASYNCHRONE LOGIK WAHREN. DIREKTES ÜBERSCHREIBEN
// VON PINS OHNE TARGET-ABGLEICH IST EIN SYSTEMFEHLER!
///////////////////////////////////////////////////////////////////////////////
// exhaust_fan.h
#ifndef exhaust_fan_H
#define exhaust_fan_H
#include <ArduinoJson.h> // <--- DAS HAT GEFEHLT!
#include <Arduino.h>

enum exhaust_fanMode {
    exhaust_fan_MODE_MANUAL,
    exhaust_fan_MODE_AUTOMATIC,
    exhaust_fan_MODE_CHAOTIC
};
void exhaust_fan_get_status(JsonObject doc);
// Funktionen
void exhaust_fan_init(uint8_t pin, uint8_t tacho_pin);
void exhaust_fan_update();
void exhaust_fan_set_speed(int percent);
void exhaust_fan_set_mode(exhaust_fanMode mode);
void exhaust_fan_set_min_speed(int percent);
void exhaust_fan_save_state();
int exhaust_fan_get_rpm(); // NEU: Um die Drehzahl abzufragen
// Einfach in die exhaust_fan.h zu den anderen Funktionen schreiben:
void exhaust_fan_process_json(JsonObject doc);
extern int current_exhaust_fan_speed;
extern exhaust_fanMode current_exhaust_fan_mode;
// TARGETS (NEU)
extern float target_temp;
extern float target_humidity;
extern int target_exhaust_fan_pct; // NEU: wie light_target

// exhaust_fan.h
extern int current_exhaust_fan_speed;      // Das ist jetzt unser MAX
extern int current_exhaust_fan_min_speed;  // NEU: Der Boden
#endif