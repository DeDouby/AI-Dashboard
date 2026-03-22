class MetricsEngine:

    def __init__(self, gsm):
        self.gsm = gsm
    # ---------------------------------------------------------
    # PROCESS SENSOR METRICS
    # ---------------------------------------------------------
    def process_metrics(self, dev_id, ch_name, ch):
        active_metrics_this_run = [] 

        metrics_to_process = {
            "temp_in": ch.get("internal", {}).get("temperature"),
            "hum_in":  ch.get("internal", {}).get("humidity"),
            "vpd_in":  ch.get("vpd_internal"),
            
            "temp_ex": ch.get("external", {}).get("temperature"),
            "hum_ex":  ch.get("external", {}).get("humidity"),
            "vpd_ex":  ch.get("vpd_external"),
        
            # --- JETZT SAUBER AUS EXTERNAL 2 ---
            "leaf_temp": ch.get("external2", {}).get("leaf_temp"),
            "vpd_leaf":  ch.get("external2", {}).get("vpd_leaf"),
            # --- NEU: Lüfter Metrik hinzufügen ---
            "fan_rpm":  ch.get("fan", {}).get("speed_rpm"),

            # Batterie bleibt im Root
            "v_bat": {"value": ch.get("battery_voltage"), "unit": "V"} if ch.get("battery_voltage") else None
        }

        # 1. Daten-Verarbeitung (Läuft für ALLE Geräte im Hintergrund)
# 1. Daten-Verarbeitung (Läuft für ALLE Geräte im Hintergrund)
        for m_name, node in metrics_to_process.items():
            # Wichtig: RPM ist oft ein Int/Float, kein Dict. 
            # Wir checken beides, damit das System nicht knallt.
            val = None
            unit = ""

            if isinstance(node, dict):
                val = node.get("value")
                unit = node.get("unit", "")
            elif isinstance(node, (int, float)):
                # Fallback für die RPM, falls sie direkt als Zahl kommt
                val = node
                unit = "RPM" if m_name == "fan_rpm" else ""

            if val is not None:
                # Key enthält Gerät und Kanal (z.B. LGS_Sensor_adv_fan_rpm)
                key = f"{dev_id}_{ch_name}_{m_name}"
                
                self.gsm.graph_engine.process_new_value(key, val)
                self.gsm.set_unit(key, unit)
                
                active_metrics_this_run.append(m_name)

        # 2. UI-Synchronisation (NUR für das aktive Gerät!)
        if dev_id == self.gsm.get_active_device_id():
            if hasattr(self.gsm, "tile_engine"):
                # Meldet der TileEngine, welche Kacheln gerade "echte" Daten haben
                self.gsm.tile_engine.register_tiles(active_metrics_this_run)

    # ---------------------------------------------------------
    # PROCESS VPD COORDINATES
    # ---------------------------------------------------------
    def process_vpd_coords(self, dev_id, ch_name, ch):
        coord = ch.get("coord", {})
        coord_internal = coord.get("internal", {})
        coord_external = coord.get("external", {})

        coord_metrics = {
            "vpd_x_in": coord_internal.get("x"),
            "vpd_y_in": coord_internal.get("y"),
            "vpd_x_ex": coord_external.get("x"),
            "vpd_y_ex": coord_external.get("y"),
        }

        # Auch Koordinaten werden simultan für alle geloggt
        for m_name, val in coord_metrics.items():
            if val is not None:
                key = f"{dev_id}_{ch_name}_{m_name}"
                self.gsm.graph_engine.process_new_value(key, val)
                self.gsm.set_unit(key, "")