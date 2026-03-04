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
        
            # --------------------------------
            # Mixed Graph Buffers reset
            # (wie frischer Start)
            # --------------------------------
            for key in ("temp", "hum", "vpd", "dew"):
        
                gk = f"mixed_avg_{key}"
        
                self.gsm.graph_engine.graph_buffers.pop(gk, None)
                self.gsm.graph_engine._trend_buffers.pop(gk, None)
                self.gsm.graph_engine._last_smoothed_values.pop(gk, None)
                self.gsm.graph_engine.global_trends.pop(gk, None)
        
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
    
            avg_value = avg
            unit = unit_map.get(key)
            
            # -----------------------------
            # TEMPERATUR UMRECHNUNG HIER !!!
            # -----------------------------
            if key == "temp" and unit == "F":
                avg_value = (avg_value - 32) * 5.0 / 9.0
                unit = "C"   # Nach Umrechnung immer C speichern
            
            results[key] = avg_value
            
            graph_key = f"mixed_avg_{key}"
            self.gsm.graph_engine.process_new_value(graph_key, avg_value)
            
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

        # FALL 1: Keine Ergebnisse da -> Datei leeren
        if not results:
            try:
                with open(path, "w") as f:
                    json.dump([], f)
                self.gsm.broadcast_engine.set_available(False)
            except Exception as e:
                print(f"[MixedEngine] Write empty failed: {e}")
            return

        # FALL 2: Daten sind da -> Berechnen und Struktur aufbauen
        try:
            temp_avg = results.get("temp")
            
            # WICHTIG: Die Struktur, die vorhin fehlte!
            json_data = [{
                "timestamp": datetime.now().isoformat(),
                "avg_temp": temp_avg,
                "avg_hum": results.get("hum"),
                "avg_vpd": results.get("vpd"),
                "avg_dew": results.get("dew"),
                "devices": device_ids or []
            }]

            # Jetzt schreiben
            with open(path, "w") as f:
                json.dump(json_data, f, indent=2)

            # Der BroadcastEngine melden, dass wir bereit sind
            self.gsm.broadcast_engine.set_available(True)

            # Automatisch starten, wenn der User es nicht explizit verboten hat
            be = self.gsm.broadcast_engine
            if not be.active and not be.user_disabled:
                be.set_active(True)

        except Exception as e:
            print(f"[MixedEngine] write_json failed: {e}")