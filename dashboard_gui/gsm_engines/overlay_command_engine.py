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
         # ====================== GROW CONTROLLER COMMANDS ======================
        elif cmd_type == "grow_controller":
            return self.send_grow_controller_command(mac, **kwargs)
    
        return None
    def send_grow_controller_command(self, mac, **kwargs):
        # 1. Aktuellen Status aus dem Buffer holen
        current = self.get_latest_device_data(mac)
        
        # 2. Die rev_grow ist unser "Gesetz"-Anker
        last_rev = int(current.get("rev_grow", 0))
        new_rev = last_rev + 1
    
        # 3. Das Payload-Paket schnüren (Target-Prinzip)
        payload = {
            "rev_grow": new_rev  # Das Ziel-Revision
        }
    
        # WiFi Daten / Mode / Commands mappen
        if "wifi_ssid" in kwargs:
            payload["wifi_ssid"] = kwargs["wifi_ssid"]
        if "wifi_pw" in kwargs:
            payload["wifi_pw"] = kwargs["wifi_pw"]
        if "wifi_mode" in kwargs:
            payload["wifi_mode"] = int(kwargs["wifi_mode"])
        if "command" in kwargs:
            payload["command"] = kwargs["command"]
    
        # 4. Abfahrt an den WEB_CLIENT
        WEB_CLIENT.send_control(mac, payload)
        
        print(f"[GrowController] TARGET-REV GESETZT: {new_rev} | Payload: {payload}")
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
    
    def send_fan_command(self, mac, **kwargs):
        # 1. Hol den aktuellen Stand aus dem Buffer
        current = self.get_latest_device_data(mac)
        
        # 2. Revision hochzählen (Das "Gesetz"-Prinzip)
        last = int(current.get("rev_circfan", 0))
        new_rev = last + 1
        
        # 3. Payload bauen
        # WICHTIG: Wir nehmen die Werte aus den kwargs (vom UI), 
        # damit wir nicht alte Werte aus dem Buffer überschreiben.
        payload = {
            "circulation_fan_min": int(kwargs.get("min", 20)),
            "circulation_fan_pct": int(kwargs.get("max", 65)),
            "circulation_fan_mode": kwargs.get("mode", "nat"),
            "rev_circfan": new_rev
        }
        
        # 4. Abfahrt
        WEB_CLIENT.send_control(mac, payload)
        print(f"[CircFan] SEND -> Rev: {new_rev} | Mode: {payload['circulation_fan_mode']}")
        
        return new_rev 
    def send_exhaust_command(self, mac, **kwargs):
        current = self.get_latest_device_data(mac)
        new_rev = int(current.get("rev_exhaust", 0)) + 1
        
        # Wir nutzen kwargs.get mit Fallbacks, um Teil-Updates (Ranges) 
        # und Voll-Updates (Mode-Wechsel) in einer Logik zu vereinen
        payload = {
            "exhaust_fan_min": int(kwargs.get("min")),
            "exhaust_fan_pct": int(kwargs.get("max")),
            "exhaust_fan_mode": kwargs.get("mode"), # Vom UI geliefert!
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