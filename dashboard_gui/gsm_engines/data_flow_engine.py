# dashboard_gui/engines/data_flow_engine.py
import time
from dashboard_gui.data_buffer import BUFFER
from datetime import datetime
class DataFlowEngine:
    def __init__(self, gsm):
        self.gsm = gsm
        
        # --- Aus GSM umgezogen ---
        self.rssi_history = {}
        self._last_state = {}
        self._last_frame_time = time.time()
        self.current_latency = 0
        self.last_seen_timestamps = {}
        # Für LED/Flow Logik
        self._last_counter = None
        self._last_raw = None

    # dashboard_gui/engines/data_flow_engine.py
    
    def process_cycle(self):
        now = time.time()
        self.current_latency = (now - self._last_frame_time) * 1000 
        self._last_frame_time = now

        BUFFER.soft_reload()
        data = BUFFER.get()
        
        if not self.gsm.running or not data:
            return

        # --- PHASE 1: SIMULTANES HINTERGRUND-UPDATE (ADV für ALLE) ---
        for device_frame in data:
            dev_id = device_frame.get("device_id")
            if not dev_id: continue
            
            # Wir checken beide Kanäle. Was "alive" ist, wird geloggt.
            # Wenn du GATT ausschaltest, ist 'gatt' nicht mehr alive -> kein Log.
            # Wenn du es einschaltest -> Log läuft simultan zum ADV der anderen!
            for ch_type in ("adv", "gatt"):
                ch_data = device_frame.get(ch_type, {})
                if isinstance(ch_data, dict) and ch_data.get("alive"):
                    self.gsm.metrics_engine.process_metrics(dev_id, ch_type, ch_data)
                    self.gsm.metrics_engine.process_vpd_coords(dev_id, ch_type, ch_data)
            # --- NEU: WEBSERVER METRICS (FEHLT KOMPLETT!) ---
                web_ch = device_frame.get("webserver", {})
                if isinstance(web_ch, dict) and web_ch.get("alive"):
                    self.gsm.metrics_engine.process_webserver_metrics(dev_id, web_ch)
            # RSSI History für den Signal-Inspector (Hintergrund)
            self._update_background_rssi(dev_id, device_frame)
        # --- PHASE 2: UI FOKUS (Aktion für das ausgewählte Gerät) ---
        from dashboard_gui.gsm_engines.active_channel_engine import ACTIVE_CHANNEL
        ch_name = ACTIVE_CHANNEL.get_active_channel()
        active_idx = ACTIVE_CHANNEL.get_active_index()

        idx = min(active_idx, len(data)-1)
        d = data[idx] 
        d["channel"] = ch_name 
                # --- WEB DATA MERGE (CLEAN FIX) ---
        from web_client import WEB_CLIENT
        
        mac = d.get("device_id")
        if mac:
            web_data = WEB_CLIENT.current_data.get(mac)
            if web_data:
                d["web"] = web_data
        dev_id = d.get("device_id")
        ch = d.get(ch_name, {})
        
        # Mixed Mode Update
        if self.gsm.mixed_mode_active:
            self.gsm.mixed_engine.update(data)

        if isinstance(ch, dict):
            # Falls wir im GATT-Kanal sind, müssen wir diesen HIER verarbeiten, 
            # da oben in Phase 1 nur ADV für alle geloggt wurde.
            if ch_name == "gatt":
                self.gsm.metrics_engine.process_metrics(dev_id, "gatt", ch)
                self.gsm.metrics_engine.process_vpd_coords(dev_id, "gatt", ch)

            # UI Daten aufbereiten
            d["_active_keys"] = self.gsm.multi_key_engine.extract_active_keys(d)
            d["latency"] = self.current_latency 
            
            if hasattr(self.gsm, 'ui_handler'):
                self.gsm.ui_handler.update_active_screen(self.gsm.screen_manager, d)
            
            # Health & LED (nur für das aktive Gerät)
            self._handle_health_and_leds(d, ch, ch_name, dev_id)
        else:
            self.gsm.led_engine.offline()
    # --- HILFSMETHODE (Die hat gefehlt!) ---
    # dashboard_gui/engines/data_flow_engine.py
    
    def _update_background_rssi(self, dev_id, frame):
        try:
            ts_value = None
            # Priorität: Root -> ADV -> GATT
            raw_ts = frame.get("timestamp") or \
                     frame.get("adv", {}).get("timestamp") or \
                     frame.get("gatt", {}).get("timestamp")

            if raw_ts:
                if isinstance(raw_ts, (int, float)):
                    ts_value = raw_ts
                elif isinstance(raw_ts, str):
                    try:
                        # ISO-Strings (z.B. 2026-03-06T04:00:00) nativ parsen
                        # Wir entfernen ein eventuelles "Z" am Ende für die Kompatibilität
                        clean_ts = raw_ts.replace("Z", "+00:00")
                        ts_value = datetime.fromisoformat(clean_ts).timestamp()
                    except ValueError:
                        # Fallback: Falls es kein ISO-String ist, nehmen wir "jetzt" 
                        # als Empfangszeitpunkt, um den Fluss nicht zu stoppen
                        ts_value = time.time()

            if ts_value:
                self.last_seen_timestamps[dev_id] = ts_value

            # RSSI History
            rssi = frame.get("health", {}).get("signal", {}).get("rssi")
            if rssi is not None:
                history = self.rssi_history.setdefault(dev_id, [])
                history.append(float(rssi))
                if len(history) > self.gsm.max_history:
                    history.pop(0)

        except Exception as e:
            print(f"[DFE] Timestamp Error for {dev_id}: {e}")
    def _handle_health_and_leds(self, d, ch, ch_name, dev_id):
        # RSSI History (intern verwaltet)
        try:
            current_rssi = d.get("health", {}).get("signal", {}).get("rssi")
            if current_rssi is not None and dev_id:
                history = self.rssi_history.setdefault(dev_id, [])
                history.append(float(current_rssi))
                if len(history) > self.gsm.max_history:
                    history.pop(0)
        except: pass

        # LED Logik
        alive = ch.get("alive", False)
        
        # NEU: Auch wenn der Kanal selbst (webserver) nicht 'alive' im BLE-Sinne ist,
        # prüfen wir, ob wir Web-Daten im Merge-Objekt haben.
        web_data = d.get("web", {})
        if ch_name == "webserver" and web_data:
            alive = True 

        if not alive:
            self.gsm.led_engine.offline()
            return

        # --- FLOW ERKENNUNG ---
        if ch_name == "webserver":
            # Wir nutzen den Zeitstempel der Web-Antwort als "Paketzähler"
            current_web_ts = web_data.get("timestamp")
            if current_web_ts and current_web_ts != getattr(self, "_last_web_ts", None):
                self.gsm.led_engine.flow()
                self._last_web_ts = current_web_ts
            else:
                self.gsm.led_engine.stale()

        elif ch_name == "adv":
            raw = ch.get("raw") or ch.get("adv_raw") or ch.get("gat_raw")
            if raw and raw != self._last_raw:
                self.gsm.led_engine.flow()
            else:
                self.gsm.led_engine.stale()
            self._last_raw = raw
            
        else: # GATT-Kanal
            counter = ch.get("packet_counter")
            if counter is not None and counter != self._last_counter:
                self.gsm.led_engine.flow()
            else:
                self.gsm.led_engine.stale()
            self._last_counter = counter