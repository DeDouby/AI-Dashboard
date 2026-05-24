import threading
import time
import requests
import json
import os
import config

class WebClientThread(threading.Thread):
    def __init__(self, interval=1.5):
        super().__init__(daemon=True)
        self.interval = interval
        self.running = True
        self.path = os.path.join(config.DATA, "web_dump.json")
        self.plants_path = os.path.join(config.DATA, "plants_store.json") 
        self.settings_path = os.path.join(config.DATA, "settings_sync.json")
        
        self.current_data = {} 
        self._last_ts = {}
        self.first_sync_done = False
        self.ready = False
        self._last_disk_write = 0.0
        self._disk_interval = 60.0  
        
        # NEU: RAM-Caches initialisieren
        self._local_plant_revs = {} 
        self._local_plants_cache = {}  # Blitztabelle im RAM für die Pflanzendaten
        
        # Beim Start einmalig Daten von Festplatte in den RAM laden
        self._load_local_plant_data_at_boot()

    def _load_local_plant_data_at_boot(self):
        """ Lädt beim Start einmalig alle Revisionsstände UND Pflanzendaten in den RAM. """
        if os.path.exists(self.plants_path):
            try:
                with open(self.plants_path, "r", encoding="utf-8") as f:
                    self._local_plants_cache = json.load(f)
                    
                    # Revisionen aus den geladenen Daten extrahieren
                    for mac, content in self._local_plants_cache.items():
                        if "plant_planner" in content:
                            self._local_plant_revs[mac] = content["plant_planner"].get("rev_plant_planner", 0)
                print("[WebClient] RAM-Cache erfolgreich geladen.")
            except Exception as e:
                print(f"[WebClient] Boot-Load Fehler: {e}")
                self._local_plants_cache = {}

    def run(self):
        while self.running:
            try:
                current_interval = config.get_refresh_interval()
                changed = self.fetch_all_web_data()
             
                now = time.time()
                if (now - self._last_disk_write) >= self._disk_interval:
                    self._save_to_disk()
                    self._last_disk_write = now
                
                time.sleep(current_interval)
            except Exception as e:
                print(f"[WebClient] Loop Error: {e}")
                time.sleep(1)

    def fetch_all_web_data(self):
        changed = False
        cfg = config._init()
        devices = cfg.get("devices", {})
        now = time.time()
        
        try:
            from decoder import inject_web_data
        except ImportError:
            return False

        for mac, dev_cfg in devices.items():
            ip = dev_cfg.get("ip_address", "").strip()
            if not ip: continue
            user, pw = config.get_device_auth(mac)
            
            try:
                r = requests.get(f"http://{ip}/data", timeout=0.7, auth=(user, pw) if user else None)
                if r.status_code == 200:
                    payload = r.json()
                    payload["timestamp"] = now 
                    
                    esp_plant_rev = payload.get("rev_plant_planner", 0)
                    local_rev = self._local_plant_revs.get(mac, -1)

                    # Nur wenn der ESP meldet, dass es was Neues gibt, wird die Festplatte/Netzwerk bemüht
                    if esp_plant_rev > local_rev:
                        self._fetch_heavy_plant_data(mac, ip, user, pw)

                    # REPARIERT: Kein "with open()" Festplatten-Zugriff mehr in der Schleife! 
                    # Daten kommen direkt und ohne Verzögerung aus dem RAM-Cache
                    if mac in self._local_plants_cache:
                        payload["plant_planner"] = (
                            self._local_plants_cache[mac]
                            .get("plant_planner", {})
                        )
                    
                    inject_web_data(mac, payload)
                    self.current_data[mac] = payload
                    changed = True
            except:
                continue
                
        self.ready = True
        return changed

    def _fetch_heavy_plant_data(self, mac, ip, user, pw):
        """ Holt große Pflanzendaten ab und aktualisiert den RAM-Cache sowie die Festplatte. """
        try:
            r = requests.get(f"http://{ip}/data/plants", timeout=2.0, auth=(user, pw) if user else None)
            if r.status_code == 200:
                plant_payload = r.json() 
                
                # RAM-Cache sofort aktualisieren
                self._local_plants_cache[mac] = plant_payload

                # Atomarer Schreibvorgang im Hintergrund auf die Festplatte
                tmp_plants = self.plants_path + ".tmp"
                with open(tmp_plants, "w", encoding="utf-8") as f:
                    json.dump(self._local_plants_cache, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_plants, self.plants_path)

                if "plant_planner" in plant_payload:
                    self._local_plant_revs[mac] = plant_payload["plant_planner"].get("rev_plant_planner", 0)
        except Exception as e:
            print(f"[WebClient] Heavy Plant Fetch Error für {mac}: {e}")

    def send_control(self, mac, payload):
        if "rev" in payload:
            try:
                data = {}
                if os.path.exists(self.settings_path):
                    with open(self.settings_path, "r") as f:
                        data = json.load(f)

                data[mac] = data.get(mac, {})
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