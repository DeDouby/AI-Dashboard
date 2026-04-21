#ifndef GROW_CONTROLLER_H
#define GROW_CONTROLLER_H

#include <Arduino.h>
#include <ArduinoJson.h>

void grow_controller_init();
void grow_controller_process_json(JsonObject doc);
void grow_controller_get_status(JsonObject doc);

#endif