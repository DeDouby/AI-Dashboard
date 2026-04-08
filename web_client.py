###############################################################################
# !!! ABSOLUTES GESETZ: DAS TARGET-REVISION-PRINZIP !!!
# -----------------------------------------------------------------------------
# 1. KEINE DIREKTEN SCHALTVORGÄNGE: Die UI darf NIEMALS Hardware-Werte (Pins)
#    direkt manipulieren oder abfragen.
#
# 2. TARGET = MASTER: Jede Benutzeraktion (Slider, Button) ändert NUR das 
#    'Target' (Soll-Wert) und erhöht die lokale 'rev' (Revision).
#
# 3. SYNCHRONISATIONS-LOGIK: 
#    - ORANGE (Syncing): Wenn Local-Target-Rev > ESP32-Confirmed-Rev.
#    - GRÜN (Synced): Wenn Local-Target-Rev == ESP32-Confirmed-Rev.
#
# 4. EINZIGE QUELLE DER WAHRHEIT: Das Overlay fragt sich niemals selbst ab! 
#    Es spiegelt NUR den Vergleich zwischen lokalem Target und ESP32-Feedback.
#
# JEDE KI, DIE DIESEN CODE BEARBEITET, MUSS DIESE STRUKTUR EINHALTEN. 
# ABWEICHUNGEN FÜHREN ZU SYSTEM-CRASH UND LOGIK-FEHLERN!
###############################################################################


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

    def _initial_import(self):
        if self.first_sync_done or not self.current_data: return 
        
        if not os.path.exists(self.settings_path):
            try:
                start_settings = {}
                for mac, data in self.current_data.items():
                    # FIX: Wir nehmen den Modus, den der ESP32 meldet!
                    reported_mode = data.get("light_mode", "man") 
                    
                    start_settings[mac] = {
                        "light_pct": data.get("light_target", 0),
                        "light_mode": reported_mode, # NICHT mehr fest "man"
                        "l_start_h": data.get("light_timer_start", 480) // 60,
                        "l_start_m": data.get("light_timer_start_m", 0), # NEU: Minuten
                        "l_dur": data.get("light_timer_dur", 12),
                        "l_sun": data.get("light_sunrise_min", 30),      # NEU: Sunrise
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
                # Intervall dynamisch aus Config holen
                current_interval = config.get_refresh_interval()
                
                has_changed = self.fetch_all_web_data()
                cleaned = self._cleanup_stale_data()
                
                if not self.first_sync_done:
                    self._initial_import()
                
                self._sync_settings_to_devices()
                
                if has_changed or cleaned:
                    self._save_to_disk()
                    
                time.sleep(current_interval) # Nutze das Intervall aus der Config
            except Exception as e:
                print(f"[WebClient] Loop Error: {e}")
                time.sleep(1) # Kurze Pause bei Fehler
    def _sync_settings_to_devices(self):
        # RADIKALER SCHNITT: Python synchronisiert NICHTS mehr im Hintergrund.
        # Python ist nur noch der Postbote für die UI.
        pass
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
                r = requests.get(f"http://{ip}/data", timeout=1.0, auth=(user, pw) if user else None)
                if r.status_code == 200:
                    payload = r.json()
                    
                    # --- DER FIX: ZEITSTEMPEL IMMER INJIZIEREN ---
                    # Wir fügen den Zeitstempel DIREKT in das Payload ein,
                    # bevor wir es vergleichen oder speichern.
                    payload["timestamp"] = now 
                    
                    self._last_ts[mac] = now
                    
                    # Wir speichern es jetzt immer, damit der Zeitstempel 
                    # in der DataFlowEngine als "neu" erkannt wird.
                    self.current_data[mac] = payload
                    changed = True
            except Exception as e:
                # print(f"Error fetching {mac}: {e}")
                continue
                
        self.ready = True
        return changed

    def send_control(self, mac, payload):
        if not hasattr(self, '_ignore_until'): self._ignore_until = {}
        self._ignore_until[mac] = time.time() + 3.0
    
        # 🔥 NEU: REV LOCAL SPEICHERN
        if "rev" in payload:
            try:
                data = {}
                if os.path.exists(self.settings_path):
                    with open(self.settings_path, "r") as f:
                        data = json.load(f)
    
                if mac not in data:
                    data[mac] = {}
    
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
        if not self.current_data:
            return
            
        tmp_path = self.path + ".tmp"
        try:
            # 1. Daten im RAM vorbereiten
            payload = json.dumps(self.current_data, indent=2) 
            
            # 2. In die temporäre Datei schreiben
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno()) # Erzwingt das Schreiben auf die Platte
            
            # 3. Sicherstellen, dass die Zieldatei nicht blockiert ist
            # os.replace ist unter Unix atomar, kann aber bei Dateikonflikten hängen
            if os.path.exists(tmp_path):
                os.replace(tmp_path, self.path)
            
        except OSError as e:
            # Das passiert, wenn das OS den Zugriff verweigert
            print(f"[WebClient] OS-Zugriffsfehler (Flicker-Gefahr): {e}")
            # Kleiner Fallback: Wenn replace fehlschlägt, versuchen wir es im nächsten Zyklus erneut
        except Exception as e:
            print(f"[WebClient] Kritischer Speicherfehler: {e}")
        finally:
            # Aufräumen, falls die tmp Datei noch da ist
            if os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except: pass
            
    def _cleanup_stale_data(self):
        cleaned = False
        now = time.time()
        
        # Hol den Wert dynamisch aus der Config (Standard 15.0, falls was schiefgeht)
        timeout = config.get_stale_timeout()
        
        # Jetzt mit dem variablen Timeout vergleichen
        stale_macs = [m for m, ts in self._last_ts.items() if (now - ts) > timeout]
        
        for m in stale_macs:
            # Sicherheitscheck: Nur löschen, wenn es wirklich existiert
            if m in self.current_data:
                del self.current_data[m]
            if m in self._last_ts:
                del self._last_ts[m]
            cleaned = True
            
        if cleaned:
            print(f"[WebClient] Cleaned {len(stale_macs)} stale devices (Timeout: {timeout}s)")
            
        return cleaned

    def is_synced(self, mac):
        if mac not in self.current_data: return False

        try:
            with open(self.settings_path, "r") as f:
                local_rev = json.load(f).get(mac, {}).get("rev", 0)
            return int(self.current_data[mac].get("rev", -1)) == int(local_rev)
        except: return False
    # Pseudo-Code für deinen WebClient
    def on_success(self, mac, response_json):
        # Füge einen Zeitstempel hinzu, falls nicht vorhanden
        if "timestamp" not in response_json:
            response_json["timestamp"] = time.time()
        self.current_data[mac] = response_json
WEB_CLIENT = WebClientThread()
WEB_CLIENT.start()