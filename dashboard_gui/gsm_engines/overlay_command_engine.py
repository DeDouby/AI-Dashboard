###############################################################################
##### !!! ABSOLUTES GESETZ: DAS TARGET-REVISION-PRINZIP (v2.0) !!! ############
###############################################################################
##### 1. HARDWARE FOLGT TARGET: Loop reagiert nur auf target vs effective.
#####    Direktes Pin-Schreiben durch UI-Input ist streng verboten!
#####
##### 2. HANDSHAKE (rev_init): Beim Öffnen des Overlays wird rev_init gesendet.
#####    Der ESP spiegelt diese NUR im RAM. Dies erzwingt ein Status-Update
#####    und bestätigt die Verbindung (Alive-Check), OHNE den Flash zu belasten.
#####
##### 3. REVISION-CONFIRMATION (rev): Der ESP bestätigt ECHTE Änderungen,
#####    indem er die rev spiegelt. Erst dann wird der Flash (Save) aktiv.
#####
##### 4. KEINE LÜGEN: Das UI zeigt "Synced" (Grün) NUR, wenn:
#####    (ui_init == esp_init) UND (ui_rev == esp_rev).
#####
##### 5. ATOMARE UPDATES: Neue Revisionen werden sofort übernommen, die
#####    Hardware (effective) zieht asynchron (z.B. über Rampen) nach.
#####
##### JEDE KI-ÄNDERUNG MUSS DIESE TRENNUNG VON RAM-PING (INIT) UND FLASH-DATA
##### (REV) WAHREN. WERTE OHNE REVISIONS-SPIEGELUNG SIND REINE LÜGEN!
###################################################################################################################################
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
            
        # --- EXHAUST FAN LOGIK ---
        elif cmd_type == "exhaust_fan":
            return self.send_exhaust_command(mac, **kwargs)
        elif cmd_type == "exhaust_fan_range":
            return self.send_exhaust_range(mac, **kwargs)
            
        elif cmd_type == "light":
            return self.send_light_command(mac, **kwargs)
        elif cmd_type == "grow_controller":
            return self.send_grow_controller_command(mac, **kwargs)
    
        return None

    # =========================================================================
    # EXHAUST FAN COMMANDS (Target-Revision v2.0)
    # =========================================================================
    
    def send_exhaust_handshake(self, mac, handshake_id):
        """
        Rein flüchtiger Ping für Exhaust Fan.
        Spiegelt rev_init_exhaust NUR im RAM des ESP (Alive-Check).
        """
        payload = {"rev_init_exhaust": int(handshake_id)}
        WEB_CLIENT.send_control(mac, payload)
        return handshake_id

    def send_exhaust_command(self, mac, **kwargs):
        """
        Zentrales Senden aller Exhaust-Parameter.
        Erhöht rev_exhaust -> ESP schreibt erst bei Revision-Match in den Flash.
        """
        current = self.get_latest_device_data(mac)
        
        # Revision hochzählen (Das Gesetz)
        last_rev = int(current.get("rev_exhaust", 0))
        new_rev = last_rev + 1
        
        # Payload nach Target-Prinzip bauen
        payload = {
            "exhaust_fan_min": int(kwargs.get("min", current.get("exhaust_fan_min", 20))),
            "exhaust_fan_pct": int(kwargs.get("max", current.get("exhaust_fan_pct", 65))),
            "exhaust_fan_mode": kwargs.get("mode", current.get("exhaust_fan_mode", "auto")),
            "exhaust_fan_chaos": bool(kwargs.get("chaos", current.get("exhaust_fan_chaos_active", False))),

            "target_temp_min": round(float(kwargs.get("t_min", current.get("target_temp_min", 22.0))), 1),
            "target_temp_max": round(float(kwargs.get("t_max", current.get("target_temp_max", 28.0))), 1),
            "target_humidity_min": int(kwargs.get("h_min", current.get("target_humidity_min", 40))),
            "target_humidity_max": int(kwargs.get("h_max", current.get("target_humidity_max", 70))),
            "target_vpd_min": round(float(kwargs.get("vpd_min", current.get("target_vpd_min", 0.8))), 1),
            "target_vpd_max": round(float(kwargs.get("vpd_max", current.get("target_vpd_max", 1.5))), 1),
            
            "rev_exhaust": new_rev
        }
        
        WEB_CLIENT.send_control(mac, payload)
        print(f"[Exhaust] TARGET-REV: {new_rev} | Mode: {payload['exhaust_fan_mode']}")
        return new_rev

    # =========================================================================
    # CIRCULATION FAN COMMANDS
    # =========================================================================

    def send_fan_handshake(self, mac, handshake_id):
        payload = {"rev_init_circfan": int(handshake_id)}
        WEB_CLIENT.send_control(mac, payload)
        return handshake_id
        
    def send_fan_command(self, mac, **kwargs):
        current = self.get_latest_device_data(mac)
        last = int(current.get("rev_circfan", 0))
        new_rev = last + 1
        
        payload = {
            "circulation_fan_min": int(kwargs.get("min", 20)),
            "circulation_fan_pct": int(kwargs.get("max", 65)),
            "circulation_fan_mode": kwargs.get("mode", "nat"),
            "rev_circfan": new_rev
        }
        
        WEB_CLIENT.send_control(mac, payload)
        return new_rev 

    # =========================================================================
    # UTILS & HELPERS
    # =========================================================================

    def get_latest_device_data(self, mac):
        """Single Source of Truth aus dem BUFFER"""
        from dashboard_gui.data_buffer import BUFFER
        for frame in BUFFER.get():
            if frame.get("device_id") == mac:
                # Wir geben den webserver-Teil zurück, falls vorhanden
                return frame.get("webserver", {})
        return {}

    def get_buffer_data(self, mac):
        return self.get_latest_device_data(mac)

    def send_grow_controller_command(self, mac, **kwargs):
        current = self.get_latest_device_data(mac)
        last_rev = int(current.get("rev_grow", 0))
        new_rev = last_rev + 1
    
        payload = {"rev_grow": new_rev}
    
        if "wifi_ssid" in kwargs: payload["wifi_ssid"] = kwargs["wifi_ssid"]
        if "wifi_pw" in kwargs: payload["wifi_pw"] = kwargs["wifi_pw"]
        if "wifi_mode" in kwargs: payload["wifi_mode"] = int(kwargs["wifi_mode"])
        if "command" in kwargs: payload["command"] = kwargs["command"]
    
        WEB_CLIENT.send_control(mac, payload)
        return new_rev

    def send_light_handshake(self, mac, handshake_id):
        payload = {"rev_init_light": handshake_id}
        WEB_CLIENT.send_control(mac, payload)

    def send_light_command(self, mac, **kwargs):
        current = self.get_latest_device_data(mac)
        last = int(current.get("rev_light", 0))
        new_rev = last + 1
        
        payload = {
            "light_pct": int(kwargs.get("pct", current.get("light_pct", 0))),
            "light_mode": kwargs.get("mode", current.get("light_mode", "man")),
            "l_start_h": int(kwargs.get("h", current.get("l_start_h", 8))),
            "l_start_m": int(kwargs.get("m", current.get("l_start_m", 0))),
            "l_dur": int(kwargs.get("dur", current.get("l_dur", 720))),
            "l_sunrise": int(kwargs.get("sunrise", current.get("l_sunrise", 60))),
            "l_sunset": int(kwargs.get("sunset", current.get("l_sunset", 60))),
            "light_climate_override": bool(kwargs.get("climate_override", current.get("light_climate_override", False))),
            "rev_light": new_rev
        }
        
        WEB_CLIENT.send_control(mac, payload)
        return new_rev
    
    def _force_resync(self, handshake_func):
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac:
            return
    
        self._my_handshake_id = int(time.time())
        handshake_func(mac, self._my_handshake_id)
    
        self._send_current_state()