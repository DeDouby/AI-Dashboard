#ifndef PLANT_PLANNER_H
#define PLANT_PLANNER_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include <vector>

// Struktur für ein einzelnes Pflanzen-Profil
struct Plant {
    String name;
    String strain;
    String breeder;
    String phenotype;
    String pot_size;
    String medium;
    String light;
    String location;
    String notes;
    String tags;
    String harvest_weight;
    String dry_weight;
    bool favorite;

    // Phasen- und Datumsfelder
    String harvest_date;
    String germination_start;
    String seedling_start;
    String vegetative_start;
    String flowering_start;
    String drying_start;
    String curing_start;
};

// Modul-Schnittstellen
void plant_planner_init();
void plant_planner_process_json(JsonObject doc);
void plant_planner_get_status(JsonObject doc);
void plant_planner_save_state();
void plant_planner_load_state();

// FIX: Exakt der Name, den die web_server.cpp aufruft
uint32_t get_plant_planner_rev(); 

#endif // PLANT_PLANNER_H