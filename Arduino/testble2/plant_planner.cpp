#include "plant_planner.h"
#include <LittleFS.h>

// Interne Modul-Variablen (Analog zu circulation_fan)
static uint32_t plant_planner_rev = 0;
static uint32_t plant_planner_init_rev = 0;
static std::vector<Plant> system_plants;

// Dateipfad für die Persistierung im Flash
static const char* STORAGE_PATH = "/plant_planner.json";

void plant_planner_init() {
    // Falls LittleFS noch nicht in der main.ino gestartet wurde, hier als Fallback
    if (!LittleFS.begin(true)) {
        Serial.println("[Plant Planner] CRITICAL: LittleFS Mount fehlgeschlagen!");
        return;
    }
    plant_planner_load_state();
    Serial.println("[Plant Planner] Modul erfolgreich geladen.");
}

void plant_planner_process_json(JsonObject doc) {
    bool flash_changed = false;

    // 1. Handshake (RAM only)
    if (doc.containsKey("rev_init_plant_planner")) {
        plant_planner_init_rev = doc["rev_init_plant_planner"];
    }

    // 2. Daten-Revision (Flash relevant)
    if (doc.containsKey("rev_plant_planner")) {
        uint32_t received_rev = doc["rev_plant_planner"];
        
        if (received_rev > plant_planner_rev) {
            plant_planner_rev = received_rev;

            // Prüfen, ob das "plant_planner" Wrapper-Objekt existiert
            if (doc.containsKey("plant_planner")) {
                JsonObject ppObj = doc["plant_planner"];
                
                if (ppObj.containsKey("plants")) {
                    JsonArray plantsArr = ppObj["plants"];
                    system_plants.clear();

                    for (JsonObject pObj : plantsArr) {
                        Plant p;
                        p.name = pObj["name"] | "";
                        p.strain = pObj["strain"] | "";
                        p.breeder = pObj["breeder"] | "";
                        p.phenotype = pObj["phenotype"] | "";
                        p.pot_size = pObj["pot_size"] | "";
                        p.medium = pObj["medium"] | "";
                        p.light = pObj["light"] | "";
                        p.location = pObj["location"] | "";
                        p.notes = pObj["notes"] | "";
                        p.tags = pObj["tags"] | "";
                        p.harvest_weight = pObj["harvest_weight"] | "";
                        p.dry_weight = pObj["dry_weight"] | "";
                        p.favorite = pObj["favorite"] | false;

                        p.harvest_date = pObj["harvest_date"] | "";
                        p.germination_start = pObj["germination_start"] | "";
                        p.seedling_start = pObj["seedling_start"] | "";
                        p.vegetative_start = pObj["vegetative_start"] | "";
                        p.flowering_start = pObj["flowering_start"] | "";
                        p.drying_start = pObj["drying_start"] | "";
                        p.curing_start = pObj["curing_start"] | "";

                        system_plants.push_back(p);
                    }
                    flash_changed = true;
                }
            }
        }
    }

    if (flash_changed) {
        plant_planner_save_state();
    }
}

void plant_planner_get_status(JsonObject doc) {
    // Erzeugt exakt die gewünschte verschachtelte Struktur im globalen Webdump
    JsonObject ppObj = doc["plant_planner"].to<JsonObject>();
    
    ppObj["rev_plant_planner"] = plant_planner_rev;
    ppObj["rev_init_plant_planner"] = plant_planner_init_rev;
    
    JsonArray plantsArr = ppObj["plants"].to<JsonArray>();
    
    for (const auto& p : system_plants) {
        JsonObject pObj = plantsArr.add<JsonObject>();
        pObj["name"] = p.name;
        pObj["strain"] = p.strain;
        pObj["breeder"] = p.breeder;
        pObj["phenotype"] = p.phenotype;
        pObj["pot_size"] = p.pot_size;
        pObj["medium"] = p.medium;
        pObj["light"] = p.light;
        pObj["location"] = p.location;
        pObj["notes"] = p.notes;
        pObj["tags"] = p.tags;
        pObj["harvest_weight"] = p.harvest_weight;
        pObj["dry_weight"] = p.dry_weight;
        pObj["favorite"] = p.favorite;

        pObj["harvest_date"] = p.harvest_date;
        pObj["germination_start"] = p.germination_start;
        pObj["seedling_start"] = p.seedling_start;
        pObj["vegetative_start"] = p.vegetative_start;
        pObj["flowering_start"] = p.flowering_start;
        pObj["drying_start"] = p.drying_start;
        pObj["curing_start"] = p.curing_start;
    }
}

void plant_planner_save_state() {
    File file = LittleFS.open(STORAGE_PATH, "w");
    if (!file) {
        Serial.println("[Plant Planner] Fehler beim Öffnen der Speicherdatei zum Schreiben!");
        return;
    }

    // Temporäres Dokument zur Serialisierung
    JsonDocument tempDoc;
    tempDoc["rev"] = plant_planner_rev;
    JsonArray arr = tempDoc["plants"].to<JsonArray>();

    for (const auto& p : system_plants) {
        JsonObject pObj = arr.add<JsonObject>();
        pObj["name"] = p.name;
        pObj["strain"] = p.strain;
        pObj["breeder"] = p.breeder;
        pObj["phenotype"] = p.phenotype;
        pObj["pot_size"] = p.pot_size;
        pObj["medium"] = p.medium;
        pObj["light"] = p.light;
        pObj["location"] = p.location;
        pObj["notes"] = p.notes;
        pObj["tags"] = p.tags;
        pObj["harvest_weight"] = p.harvest_weight;
        pObj["dry_weight"] = p.dry_weight;
        pObj["favorite"] = p.favorite;
        pObj["harvest_date"] = p.harvest_date;
        pObj["germination_start"] = p.germination_start;
        pObj["seedling_start"] = p.seedling_start;
        pObj["vegetative_start"] = p.vegetative_start;
        pObj["flowering_start"] = p.flowering_start;
        pObj["drying_start"] = p.drying_start;
        pObj["curing_start"] = p.curing_start;
    }

    if (serializeJson(tempDoc, file) == 0) {
        Serial.println("[Plant Planner] Fehler beim Schreiben der JSON-Daten!");
    }
    file.close();
}

void plant_planner_load_state() {
    if (!LittleFS.exists(STORAGE_PATH)) {
        Serial.println("[Plant Planner] Keine Profildatei gefunden. Starte leer.");
        return;
    }

    File file = LittleFS.open(STORAGE_PATH, "r");
    if (!file) return;

    JsonDocument tempDoc;
    DeserializationError error = deserializeJson(tempDoc, file);
    file.close();

    if (error) {
        Serial.println("[Plant Planner] Deserialisierungsfehler beim Laden!");
        return;
    }

    plant_planner_rev = tempDoc["rev"] | 0;
    JsonArray arr = tempDoc["plants"];
    system_plants.clear();

    for (JsonObject pObj : arr) {
        Plant p;
        p.name = pObj["name"] | "";
        p.strain = pObj["strain"] | "";
        p.breeder = pObj["breeder"] | "";
        p.phenotype = pObj["phenotype"] | "";
        p.pot_size = pObj["pot_size"] | "";
        p.medium = pObj["medium"] | "";
        p.light = pObj["light"] | "";
        p.location = pObj["location"] | "";
        p.notes = pObj["notes"] | "";
        p.tags = pObj["tags"] | "";
        p.harvest_weight = pObj["harvest_weight"] | "";
        p.dry_weight = pObj["dry_weight"] | "";
        p.favorite = pObj["favorite"] | false;
        p.harvest_date = pObj["harvest_date"] | "";
        p.germination_start = pObj["germination_start"] | "";
        p.seedling_start = pObj["seedling_start"] | "";
        p.vegetative_start = pObj["vegetative_start"] | "";
        p.flowering_start = pObj["flowering_start"] | "";
        p.drying_start = pObj["drying_start"] | "";
        p.curing_start = pObj["curing_start"] | "";

        system_plants.push_back(p);
    }
}

// FIX: Name auf get_plant_planner_rev() geändert
uint32_t get_plant_planner_rev() {
    return plant_planner_rev;
}