import os
import time
import json
import config

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
RAW_PATH = os.path.join(DATA, "ble_dump.json")


class DumpWatchdog:
    CHANNELS = ["adv", "gat", "log", "web"]  # Einheitliche Kanäle, auch wenn "web" eigentlich kein BLE-Kanal ist

    SIGNAL_FIELD = {
        "adv": "adv_raw",
        "gat": "packet_counter",
        "log": "log_raw",
        "web": "rev",  # Die Revision vom ESP32 ist unser Herzschlag
    }

    def __init__(self, timeout, interval, callback):
        self.timeout = float(timeout)
        self.interval = float(interval)
        self.callback = callback
        self._moved = {}  # mac -> {channel: bool}
        self._last_signal = {}   # mac -> {channel: value}
        self._last_ts = {}       # mac -> {channel: ts}

        self.running = False
    
    
    def _load_web(self):
        """Lädt die aktuellen Webserver-Daten"""
        path = os.path.join(DATA, "web_dump.json")
        if not os.path.exists(path): return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    
    def check_status(self):
        now = time.time()
        devices = config.get_devices()
        
        ble_dump = self._load() or []
        web_dump = self._load_web() # Dictionary {mac: {data}}
    
        per_dev = {}
        any_ok = False
    
        for mac in devices:
            ble_entry = self._find(ble_dump, mac)
            web_entry = web_dump.get(mac)
            
            dev_result = {}
            for channel in self.CHANNELS:
                # WICHTIG: Hier wird die Quelle gewechselt!
                entry = web_entry if channel == "web" else ble_entry
                
                # Nutzt deine bestehende _check_channel Logik (Movement-Check)
                ch = self._check_channel(mac, channel, entry, now)
                dev_result[channel] = ch
    
                if ch["status"] == "OK":
                    any_ok = True
    
            per_dev[mac] = dev_result
    
        return {"alive": any_ok, "status": "OK" if any_ok else "OFFLINE", "devices": per_dev}
    def _load(self):
        if not os.path.exists(RAW_PATH):
            return None
        try:
            with open(RAW_PATH, "r", encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, list) else None
        except Exception:
            return None

    def _find(self, dump, mac):
        for e in dump:
            if isinstance(e, dict) and e.get("address") == mac:
                return e
        return None

    # --------------------------------------------------------
    # EINHEITLICHE KANAL-LOGIK: Bewegung = Leben
    # --------------------------------------------------------
    def _check_channel(self, mac, channel, entry, now):
        field = self.SIGNAL_FIELD[channel]
        signal = entry.get(field) if entry else None

        if signal is None:
            return {"alive": False, "last_seen": None, "status": "OFFLINE"}

        if mac not in self._last_signal:
            self._last_signal[mac] = {}
            self._last_ts[mac] = {}
            self._moved[mac] = {}
        
        last_signal = self._last_signal[mac].get(channel)
        last_ts = self._last_ts[mac].get(channel)
        moved = self._moved[mac].get(channel, False)
        # --- FIX FÜR WEB-KANAL ---
        # Beim Webserver akzeptieren wir "Daten vorhanden" sofort als "OK"
        if channel == "web":
            self._last_ts[mac][channel] = now # Zeitstempel immer aktualisieren
            return {"alive": True, "last_seen": 0.0, "status": "OK"}
        # Initial: merken, aber NICHT alive
        if last_signal is None:
            self._last_signal[mac][channel] = signal
            self._last_ts[mac][channel] = now
            self._moved[mac][channel] = False
            return {"alive": False, "last_seen": None, "status": "INIT"}
        
        # Bewegung => alive
        if signal != last_signal:
            self._last_signal[mac][channel] = signal
            self._last_ts[mac][channel] = now
            self._moved[mac][channel] = True
            return {"alive": True, "last_seen": 0.0, "status": "OK"}
        
        # KEINE Bewegung und noch nie bewegt => bleibt tot (kein Timeout-Grace!)
        if not moved:
            return {"alive": False, "last_seen": None, "status": "INIT"}
        # Keine Bewegung → Zeit prüfen
        delta = now - (last_ts or now)

        if delta < self.timeout:
            return {"alive": True, "last_seen": delta, "status": "OK"}

        return {"alive": False, "last_seen": delta, "status": "STALE"}

    # --------------------------------------------------------

    # --------------------------------------------------------
    def start(self):
        import threading

        if self.running:
            return
        self.running = True

        def loop():
            while self.running:
                try:
                    self.callback(self.check_status())
                except Exception:
                    pass
                time.sleep(self.interval)

        threading.Thread(target=loop, daemon=True).start()

    def stop(self):
        self.running = False
