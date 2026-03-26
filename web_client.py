import threading
import time
import requests
import json
import os
import config

class WebClientThread(threading.Thread):
    def __init__(self, interval=1.3):
        super().__init__(daemon=True)
        self.interval = interval
        self.running = True
        self.path = os.path.join(config.DATA, "web_dump.json")
        self.current_data = {} # RAM-Cache für das Overlay
        self._last_ts = {}
        self.settings_path = os.path.join(config.DATA, "settings_sync.json")
        self.first_sync_done = False

    def _initial_import(self):
        if self.first_sync_done: return
        if not self.current_data: return 
        
        sync_path = self.settings_path
        if not os.path.exists(sync_path):
            print("[WebClient] Initialer Import: Erstelle settings_sync.json...")
            try:
                start_settings = {}
                for mac, data in self.current_data.items():
                    start_settings[mac] = {
                        "light_pct": data.get("light_pct", 0),
                        "light_mode": data.get("light_mode", "man"), # Licht-Modus
                        "fan_pct": data.get("fan_pct", 0),
                        "fan_min": data.get("fan_min", 0),
                        "fan_mode": data.get("fan_mode", "man"),             # Fan-Modus
                        "_last_change": 0
                    }
                
                with open(sync_path, "w") as f:
                    json.dump(start_settings, f, indent=2)
                self.first_sync_done = True
            except Exception as e:
                print(f"Import Error: {e}")
        else:
            self.first_sync_done = True
    def run(self):
        while self.running:
            has_changed = self.fetch_all_web_data()
            
            # NEU: Einmalig beim Start schauen
            if not self.first_sync_done:
                self._initial_import()
            
            # Danach wie gehabt: Soll-Zustand erzwingen
            self._sync_settings_to_devices()
            
            if has_changed:
                self._save_to_disk()
            time.sleep(self.interval)

    # Im WebClientThread
    def _sync_settings_to_devices(self):
        if not os.path.exists(self.settings_path): return
        
        try:
            with open(self.settings_path, "r") as f:
                local_data = json.load(f)
                
            changed_locally = False
            for mac, local_settings in local_data.items():
                arduino_status = self.current_data.get(mac, {})
                if not arduino_status: continue
    
                last_action = local_settings.get("_last_change", 0)
                is_user_active = (time.time() - last_action) < 10.0 
    
                # --- HIER WAR DER FEHLER: light_mode muss mit in die Liste! ---
                all_keys = ["light_pct", "fan_pct", "fan_mode", "fan_min", "light_mode"]
                
                for key in all_keys:
                    if key not in local_settings: continue
                    
                    # Wenn Soll (Lokal) != Ist (Arduino)
                    if local_settings[key] != arduino_status.get(key):
                        if is_user_active:
                            # User hat die Macht: Befehl an Arduino senden
                            self.send_control(mac, {key: local_settings[key]})
                        else:
                            # Arduino hat die Macht: Lokale Datei korrigieren (für das andere Handy)
                            local_settings[key] = arduino_status.get(key)
                            changed_locally = True
    
            if changed_locally:
                # Atomares Speichern der Korrektur
                tmp_path = self.settings_path + ".tmp"
                with open(tmp_path, "w") as f:
                    json.dump(local_data, f)
                os.replace(tmp_path, self.settings_path)
                    
        except Exception as e:
            print(f"Sync-Conflict-Error: {e}")

    def fetch_all_web_data(self):
        changed = False
        cfg = config._init()
        devices = cfg.get("devices", {})
        now = time.time()
        
        for mac, dev_cfg in devices.items():
            ip = dev_cfg.get("ip_address", "").strip()
            if not ip: continue
            
            user, pw = config.get_device_auth(mac)
            try:
                r = requests.get(f"http://{ip}/data", timeout=1.0, 
                                 auth=(user, pw) if user and pw else None)
                if r.status_code == 200:
                    payload = r.json()
                    self._last_ts[mac] = now
                    if self.current_data.get(mac) != payload:
                        self.current_data[mac] = payload
                        changed = True
            except:
                continue
        return changed

    def send_control(self, mac, payload):
        """Wird vom Overlay aufgerufen, um Befehle zu senden"""
        def _async_send():
            cfg = config._init()
            ip = cfg.get("devices", {}).get(mac, {}).get("ip_address", "")
            user, pw = config.get_device_auth(mac)
            if not ip: return
            try:
                requests.post(f"http://{ip}/control", json=payload, timeout=2.0, 
                              auth=(user, pw) if user and pw else None)
            except Exception as e:
                print(f"[WebClient] Send-Error: {e}")
        
        threading.Thread(target=_async_send, daemon=True).start()

    def _cleanup_stale_data(self):
        cleaned = False
        now = time.time()
        timeout = float(config.get_stale_timeout())
        stale_macs = [mac for mac, ts in self._last_ts.items() if (now - ts) > timeout]
        for mac in stale_macs:
            if mac in self.current_data:
                del self.current_data[mac]
                del self._last_ts[mac]
                cleaned = True
                print(f"[WebClient] {mac} is STALE. Removed.")
        return cleaned

    def _save_to_disk(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp_path = self.path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.current_data, f, indent=2)
            os.replace(tmp_path, self.path)
        except Exception as e:
            print(f"[WebClient] Write-Error: {e}")
    def sync_with_arduino_master(self, mac):
        # 1. Hol den aktuellen Status vom ESP32 (enthält Ist UND Soll)
        server_data = self.fetch_from_esp(mac) 
        local_settings = self.load_local_settings(mac)
    
        # 2. Konflikt-Lösung (Wer gewinnt?)
        # Wir führen einen "Last-Action-Timestamp" ein.
        if local_settings.get("timestamp") > server_data.get("last_change"):
            # Local gewinnt: Schicke Änderung zum ESP
            self.send_to_esp(mac, local_settings)
        else:
            # Server gewinnt: Update die lokale Datei, damit der Slider nachzieht
            self.update_local_file(mac, server_data)
# --- WICHTIG: Erst NACH der Klasse instanziieren ---
WEB_CLIENT = WebClientThread()
WEB_CLIENT.start()