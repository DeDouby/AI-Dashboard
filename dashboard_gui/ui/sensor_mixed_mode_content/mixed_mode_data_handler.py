# -*- coding: utf-8 -*-
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.data_buffer import BUFFER

class MixedModeDataHandler:
    def __init__(self, screen):
        self.screen = screen
        self.GS = GLOBAL_STATE

    def refresh(self):
        """Aktualisiert Averages und die Liste im Panel."""
        self.update_averages()
        if self.screen.panel:
            self.screen.panel.rebuild_device_list()

    def update_averages(self):
        # Wir definieren nur die Anzeigenamen
        display_names = {"temp": "TEMP", "hum": "HUM", "vpd": "VPD", "dew": "DEW"}
        
        result = {}
        for key in ["temp", "hum", "vpd", "dew"]:
            full_key = f"mixed_avg_{key}"
            
            # Wir packen nur die nackten Rohdaten in ein Dictionary
            result[key] = {
                "name": display_names[key],
                "val": self.GS.graph_engine.get_last_value(full_key),
                "unit": self.GS.get_unit(full_key) or "",
                "trend": self.GS.get_trend_icon(full_key) or ""
            }
        
        # Jetzt schicken wir das Paket (Dictionary) an das Panel
        self.screen.panel.set_averages(result)
    def get_device_list_snapshot(self):
        """Erstellt eine Liste aller Geräte mit allen Sensordetails."""
        device_list = self.GS.get_device_list()
        data = BUFFER.get() or []
        snapshot = []

        for dev_id in device_list:
            # Den passenden Datensatz (Frame) aus dem Buffer suchen
            frame = next((f for f in data if str(f.get("device_id")) == str(dev_id)), None)
            
            snapshot.append({
                "device_id": dev_id,
                "label": self.GS.ui_handler.get_device_label(dev_id),
                "frame": frame,
                "selected": dev_id in self.GS.mixed_selected_buffers,
                "has_external": frame and self._has_external(frame),
                "modes": self.GS.mixed_device_modes.get(dev_id, {"internal"}),
                # Hier werden jetzt ALLE Details generiert:
                "values_str": self._get_values_string(frame, dev_id) if frame else "Keine Daten"
            })
        return snapshot

    def _get_values_string(self, frame, dev_id):
        """Berechnet T, H, V, D für die Anzeige in der Geräteliste."""
        # Welche Sensoren sind für dieses Gerät gerade aktiv? (Internal/External)
        active_modes = self.GS.mixed_device_modes.get(dev_id, {"internal"})
        
        # Listen für die Rohwerte zum Mitteln
        t_vals, h_vals, v_vals, d_vals = [], [], [], []
        
        # Wir prüfen beide Übertragungswege (Advertising und GATT)
        for ch_name in ("adv", "gatt", "webserver"):
            ch = frame.get(ch_name, {})
            for mode in active_modes:
                m_data = ch.get(mode, {})
            
                t = m_data.get("temperature", {}).get("value")
                h = m_data.get("humidity", {}).get("value")
                v = ch.get(f"vpd_{mode}", {}).get("value")
                d = ch.get(f"dew_{mode}", {}).get("value")
            
                if t is not None: t_vals.append(float(t))
                if h is not None: h_vals.append(float(h))
                if v is not None: v_vals.append(float(v))
                if d is not None: d_vals.append(float(d))
        
        # Wenn gar nichts gefunden wurde
        if not any([t_vals, h_vals, v_vals, d_vals]):
            return "Warte auf Daten..."

        # Einheiten aus dem System holen
        u_t = self.GS.get_unit("mixed_avg_temp") or "°C"
        u_v = self.GS.get_unit("mixed_avg_vpd") or "kPa"

        # Formatierung: Jedes Detail mit 2 Nachkommastellen (:.2f)
        parts = []
        if t_vals:
            parts.append(f"T: {sum(t_vals)/len(t_vals):.2f}{u_t}")
        if h_vals:
            parts.append(f"H: {sum(h_vals)/len(h_vals):.2f}%")
        if v_vals:
            parts.append(f"V: {sum(v_vals)/len(v_vals):.2f}{u_v}")
        if d_vals:
            parts.append(f"D: {sum(d_vals)/len(d_vals):.2f}{u_t}")

        # Zusammenfügen mit Trenner (z.B. T: 24.50°C | H: 55.00% | ...)
        return " | ".join(parts)
    
    
    def _has_external(self, frame):
        """Prüft, ob das Gerät Hardware für externe Sensoren besitzt (jetzt inkl. Webserver)."""
        if not frame: return False
        # Wir loopen durch alle Kanäle
        for ch_name in ("adv", "gatt", "webserver"):
            ch = frame.get(ch_name, {})
            if ch.get("external", {}).get("present"): 
                return True
        return False

    def refresh(self):
        """Komplettes Refresh der UI (Liste neu bauen)."""
        self.update_averages()
        if self.screen.panel:
            self.screen.panel.rebuild_device_list()

    def update_live_data(self):
        """Nur die Werte aktualisieren (für den Timer/Loop)."""
        self.update_averages()
        if self.screen.panel:
            self.screen.panel.update_device_values()
