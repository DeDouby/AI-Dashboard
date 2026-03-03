class MetricsEngine:

    def __init__(self, gsm):
        self.gsm = gsm

    # ---------------------------------------------------------
    # PROCESS SENSOR METRICS
    # ---------------------------------------------------------
    def process_metrics(self, dev_id, ch_name, ch):

        metrics_to_process = {
            "temp_in": ch.get("internal", {}).get("temperature"),
            "hum_in":  ch.get("internal", {}).get("humidity"),
            "vpd_in":  ch.get("vpd_internal"),
            "temp_ex": ch.get("external", {}).get("temperature"),
            "hum_ex":  ch.get("external", {}).get("humidity"),
            "vpd_ex":  ch.get("vpd_external"),
        }

        for m_name, node in metrics_to_process.items():
            if isinstance(node, dict) and node.get("value") is not None:

                val = node.get("value")
                unit = node.get("unit", "")

                key = f"{dev_id}_{ch_name}_{m_name}"

                self.gsm.graph_engine.process_new_value(key, val)
                self.gsm.set_unit(key, unit)


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