# dashboard_gui/engines/data_flow_engine.py
import time
from dashboard_gui.data_buffer import BUFFER

class DataFlowEngine:
    def __init__(self, gsm):
        self.gsm = gsm
        
        # --- Aus GSM umgezogen ---
        self.rssi_history = {}
        self._last_state = {}
        self._last_frame_time = time.time()
        self.current_latency = 0
        
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

            # RSSI History für den Signal-Inspector (Hintergrund)
            self._update_background_rssi(dev_id, device_frame)
        # --- PHASE 2: UI FOKUS (Aktion für das ausgewählte Gerät) ---
        from dashboard_gui.engines.active_channel_engine import ACTIVE_CHANNEL
        ch_name = ACTIVE_CHANNEL.get_active_channel()
        active_idx = ACTIVE_CHANNEL.get_active_index()

        idx = min(active_idx, len(data)-1)
        d = data[idx] 
        d["channel"] = ch_name 
        
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
    def _update_background_rssi(self, dev_id, frame):
        try:
            rssi = frame.get("health", {}).get("signal", {}).get("rssi")
            if rssi is not None:
                history = self.rssi_history.setdefault(dev_id, [])
                history.append(float(rssi))
                if len(history) > self.gsm.max_history:
                    history.pop(0)
        except:
            pass

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
        if not alive:
            self.gsm.led_engine.offline()
            return

        counter = ch.get("packet_counter")
        raw = ch.get("raw") or ch.get("adv_raw") or ch.get("gat_raw")

        if ch_name == "adv":
            if raw and raw != self._last_raw:
                self.gsm.led_engine.flow()
            else:
                self.gsm.led_engine.stale()
            self._last_raw = raw
        else: 
            if counter != self._last_counter:
                self.gsm.led_engine.flow()
            else:
                self.gsm.led_engine.stale()
            self._last_counter = counter