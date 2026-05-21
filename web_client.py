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
        # NEU: Separater Pfad für die Pflanzendaten auf der Festplatte
        self.plants_path = os.path.join(config.DATA, "plants_store.json") 
        self.current_data = {} 
        self._last_ts = {}
        self.settings_path = os.path.join(config.DATA, "settings_sync.json")
        self.first_sync_done = False
        self.ready = False
        self._last_disk_write = 0.0
        self._disk_interval = 60.0  # Minütlicher Klima-Dump
        
        # NEU: RAM-Cache für den Revisions-Abgleich pro ESP32-MAC
        self._local_plant_revs = {} 
        self._load_local_plant_revs()



    def run(self):
        while self.running:
            try:
                current_interval = config.get_refresh_interval()
                
                # Nur speichern, wenn sich wirklich was geändert hat (Empfang erfolgreich)
                changed = self.fetch_all_web_data()
             
                # 🔥 DISK THROTTLE
                now = time.time()
                if (now - self._last_disk_write) >= self._disk_interval:
                    self._save_to_disk()
                    self._last_disk_write = now
                
                # BLE-Modus: Kein Cleanup mehr! Stale Daten bleiben einfach stehen.
                
                time.sleep(current_interval)
            except Exception as e:
                print(f"[WebClient] Loop Error: {e}")
                time.sleep(1)
    


    def _load_local_plant_revs(self):
        """ Lädt beim Start den aktuellen Revisionsstand der Pflanzen von Disk. """
        if os.path.exists(self.plants_path):
            try:
                with open(self.plants_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for mac, content in data.items():
                        # Holt die "rev_plant_planner" aus dem gespeicherten Objekt
                        if "plant_planner" in content:
                            self._local_plant_revs[mac] = content["plant_planner"].get("rev_plant_planner", 0)
            except:
                pass

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
            
            # 1. SCHLANKE KLIMADATEN ABHOLEN (/data)
            try:
                r = requests.get(f"http://{ip}/data", timeout=0.7, auth=(user, pw) if user else None)
                if r.status_code == 200:
                    payload = r.json()
                    payload["timestamp"] = now 
                    
                    # Holt die flache Revisionsnummer aus dem Payload
                    esp_plant_rev = payload.get("rev_plant_planner", 0)
                    local_rev = self._local_plant_revs.get(mac, -1)

                    # 2. LAZY LOADING: Nur wenn der ESP32 eine neuere Revision meldet
                    if esp_plant_rev > local_rev:
                        self._fetch_heavy_plant_data(mac, ip, user, pw)

                    # Injektion in den Decoder (NUR Klimadaten, da payload kein "plant_planner" enthält)
                    # =========================================================
                    # PLANTS IN PAYLOAD MERGEN
                    # =========================================================
                    
                    if os.path.exists(self.plants_path):
                        try:
                            with open(self.plants_path, "r", encoding="utf-8") as f:
                                all_plants = json.load(f)
                    
                            if mac in all_plants:
                                payload["plant_planner"] = (
                                    all_plants[mac]
                                    .get("plant_planner", {})
                                )
                    
                        except Exception as e:
                            print(f"[PlantPlanner] Merge Error: {e}")
                    
                    # =========================================================
                    # JETZT ERST IN BUFFER
                    # =========================================================
                    
                    inject_web_data(mac, payload)
                    
                    self.current_data[mac] = payload
                    changed = True
            except:
                continue
                
        self.ready = True
        return changed

    def _fetch_heavy_plant_data(self, mac, ip, user, pw):
        """ Holt die großen Pflanzendaten isoliert ab und speichert sie atomar. """
        try:
            r = requests.get(f"http://{ip}/data/plants", timeout=2.0, auth=(user, pw) if user else None)
            if r.status_code == 200:
                plant_payload = r.json() # Enthält {"plant_planner": {"rev_plant_planner": X, "plants": [...]}}
                
                # Bestehende Datei lesen oder neu anlegen
                all_plants = {}
                if os.path.exists(self.plants_path):
                    with open(self.plants_path, "r", encoding="utf-8") as f:
                        try: all_plants = json.load(f)
                        except: pass

                # Daten für diese spezifische MAC-Adresse updaten
                all_plants[mac] = plant_payload

                # Atomarer Schreibvorgang auf die Festplatte (plants_store.json)
                tmp_plants = self.plants_path + ".tmp"
                with open(tmp_plants, "w", encoding="utf-8") as f:
                    json.dump(all_plants, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_plants, self.plants_path)

                # Internen RAM-Cache updaten, damit nicht nochmal gefetched wird
                if "plant_planner" in plant_payload:
                    self._local_plant_revs[mac] = plant_payload["plant_planner"].get("rev_plant_planner", 0)
                    print(f"[WebClient] Pflanzen-Revision für {mac} erfolgreich auf {self._local_plant_revs[mac]} aktualisiert.")
        except Exception as e:
            print(f"[WebClient] Heavy Plant Fetch Error für {mac}: {e}")

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