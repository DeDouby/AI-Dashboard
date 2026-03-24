import threading, time, requests, json, os
import config

class WebClientThread(threading.Thread):
    def __init__(self, interval=1.0):
        super().__init__(daemon=True)
        self.interval = interval
        self.running = True
        self.path = os.path.join(config.DATA, "web_dump.json")
        self._last_ts = {}  # Merkt sich, wann welches Gerät zuletzt online war
        self.current_data = self._load_initial_data()
        self.first_run = True 

    def _load_initial_data(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: pass
        return {}

    def run(self):
        while self.running:
            # 1. Daten abrufen
            has_changed = self.fetch_all_web_data()
            
            # 2. Prüfen, ob Geräte "stale" (abgelaufen) sind
            was_cleaned = self._cleanup_stale_data()
            
            # 3. Schreiben wenn: Erster Lauf ODER Daten neu ODER Gerät abgelaufen
            if has_changed or was_cleaned or self.first_run:
                self._save_to_disk()
                self.first_run = False 
                
            time.sleep(self.interval)

    def fetch_all_web_data(self):
        changed = False
        cfg = config._init()
        devices = cfg.get("devices", {})
        now = time.time()
        
        for mac, dev_cfg in devices.items():
            ip = dev_cfg.get("ip_address", "").strip()
            if not ip: continue
            
            url = f"http://{ip}/data"
            try:
                response = requests.get(url, timeout=1.5, headers={
                    'User-Agent': 'Mobile-ESP-App',
                    'Connection': 'close'
                })
                
                if response.status_code == 200:
                    new_payload = response.json()
                    self._last_ts[mac] = now # Zeitstempel aktualisieren
                    
                    if self.current_data.get(mac) != new_payload:
                        self.current_data[mac] = new_payload
                        changed = True
            except:
                # Bei Fehler (ESP offline) machen wir hier nichts, 
                # cleanup_stale_data übernimmt das Löschen nach Timeout
                continue
        return changed

    def _cleanup_stale_data(self):
        """ Entfernt abgelaufene Geräte und gibt True zurück, wenn gelöscht wurde """
        cleaned = False
        now = time.time()
        timeout = float(config.get_stale_timeout())
        
        # Liste der MACs, die zu lange nicht gesehen wurden
        stale_macs = [mac for mac, ts in self._last_ts.items() if (now - ts) > timeout]
        
        for mac in stale_macs:
            if mac in self.current_data:
                del self.current_data[mac]
                del self._last_ts[mac]
                cleaned = True
                print(f"python: [WebClient] {mac} is STALE. Removing from dump.")
        return cleaned

    def _save_to_disk(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp_path = self.path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.current_data, f, indent=2)
            os.replace(tmp_path, self.path)
        except Exception as e:
            print(f"python: [WebClient] Write-Error: {e}")