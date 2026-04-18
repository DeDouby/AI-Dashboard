# In dashboard_gui/gsm_engines/overlay_command_engine.py
import time
from web_client import WEB_CLIENT

class OverlayCommandEngine:
    def __init__(self, gsm):
        self.gsm = gsm

    def process_command(self, mac, cmd_type, **kwargs):
        if cmd_type == "circulation_fan":
            return self.send_fan_command(mac, **kwargs)
        elif cmd_type == "circulation_fan_range":
            return self.send_fan_range(mac, **kwargs)
            
        # --- NEU: EXHAUST FAN LOGIK ---
        elif cmd_type == "exhaust_fan":
            return self.send_exhaust_command(mac, **kwargs)
        elif cmd_type == "exhaust_fan_range":
            return self.send_exhaust_range(mac, **kwargs)
        elif cmd_type == "light":
            return self.send_light_command(mac, **kwargs)
        return None

    def send_fan_command(self, mac, **kwargs):
        last = self.get_latest_device_data(mac).get("rev_circfan", 0)
        new_rev = last + 1
        payload = {
            "circulation_fan_min": int(kwargs.get("min", 20)),
            "circulation_fan_pct": int(kwargs.get("max", 65)),
            "circulation_fan_mode": kwargs.get("mode", "nat"),
            "rev_circfan": new_rev
        }
        WEB_CLIENT.send_control(mac, payload)
        return new_rev
    def send_fan_range(self, mac, **kwargs):
        current = self.get_latest_device_data(mac)
        last = int(current.get("rev_circfan", 0))
        new_rev = last + 1        # kwargs muss jetzt den mode enthalten, den das Overlay lokal verwaltet!
        payload = {
            "circulation_fan_min": int(kwargs.get("min")),
            "circulation_fan_pct": int(kwargs.get("max")),
            "circulation_fan_mode": kwargs.get("mode"), # NIEMALS aus get_latest_device_data holen!
            "rev_circfan": new_rev
        }
        WEB_CLIENT.send_control(mac, payload)
        return new_rev
    def send_exhaust_command(self, mac, **kwargs):
        """Sendet komplettes Set inkl. Modus-Wechsel"""
        last = self.get_latest_device_data(mac).get("rev_exhaust", 0)
        new_rev = last + 1
        payload = {
            "exhaust_fan_min": int(kwargs.get("min", 20)),
            "exhaust_fan_pct": int(kwargs.get("max", 65)),
            "exhaust_fan_mode": kwargs.get("mode", "auto"),
            "target_temp_min": int(kwargs.get("t_min", 22)),
            "target_temp_max": int(kwargs.get("t_max", 28)),
            "target_humidity_min": int(kwargs.get("h_min", 40)),
            "target_humidity_max": int(kwargs.get("h_max", 70)),
            "target_vpd_min": float(kwargs.get("vpd_min", 0.8)),
            "target_vpd_max": float(kwargs.get("vpd_max", 1.5)),
            "rev_exhaust": new_rev
        }
        WEB_CLIENT.send_control(mac, payload)
        return new_rev

    def send_exhaust_range(self, mac, **kwargs):
        """Update nur für Slider-Änderungen (behält aktuellen Modus)"""
        last = self.get_latest_device_data(mac).get("rev_exhaust", 0)
        new_rev = last + 1
        current_data = self.get_latest_device_data(mac)
        
        payload = {
            "exhaust_fan_min": int(kwargs.get("min")),
            "exhaust_fan_pct": int(kwargs.get("max")),
            "exhaust_fan_mode": current_data.get("exhaust_fan_mode", "auto"),
            "target_temp_min": int(kwargs.get("t_min")),
            "target_temp_max": int(kwargs.get("t_max")),
            "target_humidity_min": int(kwargs.get("h_min")),
            "target_humidity_max": int(kwargs.get("h_max")),
            "target_vpd_min": float(kwargs.get("vpd_min")),
            "target_vpd_max": float(kwargs.get("vpd_max")),
            "rev_exhaust": new_rev
        }
        WEB_CLIENT.send_control(mac, payload)
        return new_rev



 # === DIE KORREKTUR DER SCHWACHSTELLE ===

    def get_latest_device_data(self, mac):
        """Holt die decodierten Daten aus dem BUFFER (Single Source of Truth)"""
        from dashboard_gui.data_buffer import BUFFER
        for frame in BUFFER.get():
            if frame.get("device_id") == mac:
                return frame.get("webserver", {})
        return {}

    def get_buffer_data(self, mac):
        
        return self.get_latest_device_data(mac)
    
    def send_light_command(self, mac, **kwargs):
        """Zentraler Befehl für Licht (Modus, Helligkeit, Timer)"""
        last = self.get_latest_device_data(mac).get("rev_light", 0)
        new_rev = last + 1
        
        # Wir bauen das Payload-Paket
        payload = {
            "light_pct": int(kwargs.get("pct", 0)),
            "light_mode": kwargs.get("mode", "man"),
            "l_start_h": int(kwargs.get("h", 8)),
            "l_start_m": int(kwargs.get("m", 0)),
            "l_dur": int(kwargs.get("dur", 720)),
            "l_sunrise": int(kwargs.get("sunrise", 60)),
            "l_sunset": int(kwargs.get("sunset", 60)),
            "rev_light": new_rev
        }
        
        WEB_CLIENT.send_control(mac, payload)
        return new_rev