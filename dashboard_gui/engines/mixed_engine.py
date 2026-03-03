# dashboard_gui/mixed_engine.py
import os
import json
from datetime import datetime
class MixedEngine:

    def __init__(self, gsm):
        self.gsm = gsm

    # ---------------------------------------------------------
    # UPDATE
    # ---------------------------------------------------------
    def update(self, all_data):
    
        selected = self.gsm.mixed_selected_buffers
    
        if not selected or not all_data:
            self.write_json([])
            return
    
        averaging_map = {"temp": [], "hum": [], "vpd": [], "dew": []}
        unit_map = {"temp": None, "hum": None, "vpd": None, "dew": None}
        active_device_ids = []
    
        for frame in all_data:
    
            dev_id = str(frame.get("device_id"))
    
            if dev_id not in selected:
                continue
    
            active_modes = self.gsm.mixed_device_modes.get(dev_id, {"internal"})
    
            for ch_name in ("adv", "gatt"):
    
                ch = frame.get(ch_name)
                if not isinstance(ch, dict):
                    continue
    
                for mode in active_modes:
    
                    vals = ch.get(mode)
                    if not isinstance(vals, dict):
                        continue
    
                    temp_node = vals.get("temperature", {})
                    hum_node = vals.get("humidity", {})
    
                    t = temp_node.get("value")
                    h = hum_node.get("value")
    
                    if t is not None:
                        averaging_map["temp"].append(float(t))
                        if unit_map["temp"] is None:
                            unit_map["temp"] = temp_node.get("unit")
    
                    if h is not None:
                        averaging_map["hum"].append(float(h))
                        if unit_map["hum"] is None:
                            unit_map["hum"] = hum_node.get("unit")
    
                    v_key = f"vpd_{mode}"
                    d_key = f"dew_point_{mode}"
    
                    v_node = ch.get(v_key, {})
                    d_node = ch.get(d_key, {})
    
                    v = v_node.get("value")
                    d = d_node.get("value")
    
                    if v is not None:
                        averaging_map["vpd"].append(float(v))
                        if unit_map["vpd"] is None:
                            unit_map["vpd"] = v_node.get("unit")
    
                    if d is not None:
                        averaging_map["dew"].append(float(d))
                        if unit_map["dew"] is None:
                            unit_map["dew"] = d_node.get("unit")
    
            active_device_ids.append(dev_id)
    
        results = {}
        has_real_data = False
    
        for key, vals in averaging_map.items():
    
            if not vals:
                results[key] = None
                continue
    
            avg = sum(vals) / len(vals)
            graph_key = f"mixed_avg_{key}"
    
            results[key] = avg
    
            self.gsm.graph_engine.process_new_value(graph_key, avg)
    
            unit = unit_map.get(key)
            if unit:
                self.gsm.set_unit(graph_key, unit)
    
            has_real_data = True
    
        if not has_real_data:
            self.write_json([])
            return
    
        self.write_json(results, active_device_ids)

    def init_file(self):
    
        path = os.path.join("data", "mixed.json")
    
        try:
    
            with open(path, "w", encoding="utf-8") as f:
                json.dump([], f)
    
            self.gsm.broadcast_data_available = False
    
            print(f"[MixedEngine] mixed.json initialisiert: {path}")
    
        except Exception as e:
    
            print(f"[MixedEngine] mixed.json init failed: {e}")

    def check_file(self):
    
        path = os.path.join("data", "mixed.json")
    
        if not os.path.exists(path):
            return False
    
        try:
    
            with open(path, "r") as f:
                data = json.load(f)
    
            return bool(data)
    
        except:
            return False

    def write_json(self, results, device_ids=None):
    
        path = os.path.join("data", "mixed.json")
    
        # --------------------------------
        # FALL 1: KEINE DATEN
        # --------------------------------
        if not results:
    
            with open(path, "w") as f:
                json.dump([], f)
    
            self.gsm.broadcast_data_available = False
    
            try:
                import core
                core.stop_broadcast_bridge()
            except:
                pass
    
            self.gsm.set_broadcast_active(False)
            self.gsm.refresh_all_headers()
    
            return
    
        # --------------------------------
        # FALL 2: DATEN
        # --------------------------------
        json_data = [{
            "timestamp": datetime.now().isoformat(),
            "avg_temp": results.get("temp"),
            "avg_hum": results.get("hum"),
            "avg_vpd": results.get("vpd"),
            "avg_dew": results.get("dew"),
            "devices": device_ids
        }]
    
        with open(path, "w") as f:
            json.dump(json_data, f, indent=2)
    
        self.gsm.broadcast_data_available = True
    
        if not self.gsm.broadcast_active and not self.gsm.broadcast_user_disabled:
    
            try:
                import core
                core.start_broadcast_bridge()
                self.gsm.set_broadcast_active(True)
            except:
                pass
    
        self.gsm.refresh_all_headers()