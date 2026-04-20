class MetricsEngine:

    def __init__(self, gsm):
        self.gsm = gsm

    # ---------------------------------------------------------
    # PROCESS SENSOR METRICS
    # ---------------------------------------------------------
    def process_metrics(self, dev_id, ch_name, ch):
        active_metrics_this_run = []
        ble = ch.get("ble_sensors", {})
        sps = ble.get("sps", {})
        tb2 = ble.get("tb2", {})
        metrics_to_process = {
            "temp_in": ch.get("internal", {}).get("temperature"),
            "hum_in":  ch.get("internal", {}).get("humidity"),
            "vpd_in":  ch.get("vpd_internal"),
            "temp_ex": ch.get("external", {}).get("temperature"),
            "hum_ex":  ch.get("external", {}).get("humidity"),
            "vpd_ex":  ch.get("vpd_external"),
            "leaf_temp": ch.get("external2", {}).get("leaf_temp"),
            "vpd_leaf":  ch.get("external2", {}).get("vpd_leaf"),
            "circulation_fan_rpm": ch.get("circulation_fan", {}).get("circulation_fan_rpm"),
            "exhaust_fan_rpm": ch.get("exhaust_fan", {}).get("exhaust_fan_rpm"),

            # --- BLE SENSORS (NEUE STRUKTUR) ---
            "ble_temp_sps": sps.get("temperature"),
            "ble_hum_sps":  sps.get("humidity"),
            "ble_vpd_sps":  sps.get("vpd"),
            
            "ble_temp_tb2": tb2.get("temperature"),
            "ble_hum_tb2":  tb2.get("humidity"),
            "ble_vpd_tb2":  tb2.get("vpd"),

            "v_bat": {"value": ch.get("battery_voltage"), "unit": "V"} if ch.get("battery_voltage") else None
        }

# --- 1. Daten-Verarbeitung ---
        for m_name, value_node in metrics_to_process.items():
            val = None
            unit = ""

            if isinstance(value_node, dict):
                # Neue Struktur (wie bei exhaust_fan)
                val = value_node.get("value") or value_node.get(m_name)  # fallback
                unit = value_node.get("unit", "")
            elif isinstance(value_node, (int, float)):
                # Alte Struktur (reiner Wert)
                val = value_node
                # Unit automatisch setzen
                if "fan_rpm" in m_name:
                    unit = "RPM"
                elif m_name.startswith("vpd"):
                    unit = "kPa"
                elif m_name.startswith("temp") or m_name == "leaf_temp":
                    unit = "°C"
                elif m_name.startswith("hum"):
                    unit = "%"

            if val is not None:
                key = f"{dev_id}_{ch_name}_{m_name}"
                self.gsm.graph_engine.process_new_value(key, val)
                self.gsm.set_unit(key, unit)
                active_metrics_this_run.append(m_name)

        # --- 2. UI-Synchronisation ---
        if dev_id == self.gsm.get_active_device_id():
            if hasattr(self.gsm, "tile_engine"):
                self.gsm.tile_engine.register_tiles(active_metrics_this_run)
                
                
# ---------------------------------------------------------
    # PROCESS VPD COORDINATES (FIXED)
    # ---------------------------------------------------------
    def process_vpd_coords(self, dev_id, ch_name, ch):
        coord = ch.get("coord", {})
        coord_internal = coord.get("internal", {})
        coord_external = coord.get("external", {})
        
        # Basis-Koordinaten (Internal / External)
        all_coords = {
            "vpd_x_in": coord_internal.get("x"),
            "vpd_y_in": coord_internal.get("y"),
            "vpd_x_ex": coord_external.get("x"),
            "vpd_y_ex": coord_external.get("y"),
        }

        # --- BLE COORDS HINZUFÜGEN ---
        ble = ch.get("ble_sensors", {})
        sps = ble.get("sps", {})
        tb2 = ble.get("tb2", {})
        
        # Wir erweitern das Dictionary um die BLE-Werte
        all_coords.update({
            "vpd_x_sps": sps.get("coord", {}).get("x"),
            "vpd_y_sps": sps.get("coord", {}).get("y"),
            "vpd_x_tb2": tb2.get("coord", {}).get("x"),
            "vpd_y_tb2": tb2.get("coord", {}).get("y"),
        })

        # --- ALLE KOORDINATEN PROZESSIEREN ---
        for m_name, val in all_coords.items():
            if val is not None:
                key = f"{dev_id}_{ch_name}_{m_name}"
                self.gsm.graph_engine.process_new_value(key, val)
                self.gsm.set_unit(key, "")

    # ---------------------------------------------------------
    # NEU: Webserver-Support für Fullscreen & Graphs
    # ---------------------------------------------------------
    def process_webserver_metrics(self, dev_id, ch):
        """Sorgt dafür, dass Webserver-Kanal Graphen bekommt."""
        self.process_metrics(dev_id, "webserver", ch)
        self.process_vpd_coords(dev_id, "webserver", ch)
