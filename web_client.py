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
        self.current_data = {} 
        self._last_ts = {}
        self.settings_path = os.path.join(config.DATA, "settings_sync.json")
        self.first_sync_done = False
        self.ready = False

        # Beim Start: Bestehenden Dump laden (BLE-Like: Wir starten mit dem letzten bekannten Stand)
        if os.path.exists(self.path):
            try:
                with open(self.path, "r") as f:
                    self.current_data = json.load(f)
            except:
                self.current_data = {}

    def _initial_import(self):
        if self.first_sync_done or not self.current_data: return 
        
        if not os.path.exists(self.settings_path):
            try:
                start_settings = {}
                for mac, data in self.current_data.items():
                    start_settings[mac] = {
                        "light_pct": data.get("light_target", 0),
                        "light_mode": data.get("light_mode", "man"),
                        "l_start_h": data.get("light_timer_start", 480) // 60,
                        "l_start_m": data.get("light_timer_start_m", 0),
                        "l_dur": data.get("light_timer_dur", 12),
                        "l_sun": data.get("light_sunrise_min", 30),
                        "rev": int(data.get("rev", 0)),
                        "_last_change": 0
                    }
                with open(self.settings_path, "w") as f:
                    json.dump(start_settings, f, indent=2)
                self.first_sync_done = True
            except Exception as e:
                print(f"[WebClient] Import Error: {e}")

    def run(self):
        while self.running:
            try:
                current_interval = config.get_refresh_interval()
                
                # Nur speichern, wenn sich wirklich was geändert hat (Empfang erfolgreich)
                if self.fetch_all_web_data():
                    if not self.first_sync_done:
                        self._initial_import()
                    self._save_to_disk()
                
                # BLE-Modus: Kein Cleanup mehr! Stale Daten bleiben einfach stehen.
                
                time.sleep(current_interval)
            except Exception as e:
                print(f"[WebClient] Loop Error: {e}")
                time.sleep(1)

    def fetch_all_web_data(self):
        changed = False
        cfg = config._init()
        devices = cfg.get("devices", {})
        now = time.time()
        
        # LOCAL IMPORT um Circular Imports zu killen
        try:
            from decoder import inject_web_data
        except ImportError:
            return False

        for mac, dev_cfg in devices.items():
            ip = dev_cfg.get("ip_address", "").strip()
            if not ip: continue
            user, pw = config.get_device_auth(mac)
            try:
                r = requests.get(f"http://{ip}/data", timeout=1.2, auth=(user, pw) if user else None)
                if r.status_code == 200:
                    payload = r.json()
                    payload["timestamp"] = now 
                    
                    # JETZT DIE INJECTION
                    inject_web_data(mac, payload)
                    
                    self.current_data[mac] = payload
                    changed = True
            except:
                continue
                
        self.ready = True
        return changed

    def send_control(self, mac, payload):
        """ Target-Revision-Prinzip: Wir schreiben nur das neue Target vorab. """
        if "rev" in payload:
            try:
                data = {}
                if os.path.exists(self.settings_path):
                    with open(self.settings_path, "r") as f:
                        data = json.load(f)

                if mac not in data: data[mac] = {}
                data[mac]["rev"] = int(payload["rev"])

                with open(self.settings_path, "w") as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                print(f"[REV SAVE ERROR]: {e}")

        def _async_send():
            cfg = config._init()
            ip = cfg.get("devices", {}).get(mac, {}).get("ip_address", "")
            user, pw = config.get_device_auth(mac)
            if not ip: return
            try:
                requests.post(f"http://{ip}/control", json=payload, timeout=2.0, auth=(user, pw) if user else None)
            except: pass
        threading.Thread(target=_async_send, daemon=True).start()

    def _save_to_disk(self):
        """ Atomares Schreiben des aktuellen RAM-Zustands. """
        tmp_path = self.path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.current_data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.path)
        except Exception as e:
            print(f"[WebClient] Write Error: {e}")

    def is_synced(self, mac):
        if mac not in self.current_data: return False
        try:
            with open(self.settings_path, "r") as f:
                local_rev = json.load(f).get(mac, {}).get("rev", 0)
            return int(self.current_data[mac].get("rev", -1)) == int(local_rev)
        except: return False

WEB_CLIENT = WebClientThread()
WEB_CLIENT.start()