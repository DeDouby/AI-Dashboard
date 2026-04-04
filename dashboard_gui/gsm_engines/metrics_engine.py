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
            "leaf_temp": ch.get("external2", {}).get("leaf_temp"),
            "vpd_leaf":  ch.get("external2", {}).get("vpd_leaf"),
            "circulation_fan_rpm": ch.get("circulation_fan", {}).get("circulation_fan_rpm"),
            "v_bat": {"value": ch.get("battery_voltage"), "unit": "V"} if ch.get("battery_voltage") else None
        }

        # --- 1. Daten-Verarbeitung (für ALLE Kanäle, inkl. webserver) ---
        for m_name, node in metrics_to_process.items():
            val = None
            unit = ""

            if isinstance(node, dict):
                val = node.get("value")
                unit = node.get("unit", "")
            elif isinstance(node, (int, float)):
                val = node
                unit = "RPM" if m_name == "circulation_fan_rpm" else ""

            if val is not None:
                key = f"{dev_id}_{ch_name}_{m_name}"
                self.gsm.graph_engine.process_new_value(key, val)
                self.gsm.set_unit(key, unit)
                active_metrics_this_run.append(m_name)

        # --- 2. UI-Synchronisation (nur für aktives Gerät) ---
        if dev_id == self.gsm.get_active_device_id():
            if hasattr(self.gsm, "tile_engine"):
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

        for m_name, val in coord_metrics.items():
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
