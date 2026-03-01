# dashboard_gui/global_state_manager.py
# HEARTBEAT + MULTI-DEVICE – CLEAN VERSION

from kivy.clock import Clock
from dashboard_gui.data_buffer import BUFFER
import time
import config
def _extract_mac(dev):
    """Normiert device_id auf reine MAC."""
    if isinstance(dev, dict):
        return dev.get("device_id")
    return dev


class GlobalStateManager:
    def __init__(self):
        # Run-State
        self.running = True
        # in __init__
        self._flow_hold = False

        # Screen Refs
        self.dashboard_ref = None
        self.fullscreen_ref = None
        self.setup_ref = None
        self.about_ref = None
        self.settings_ref = None
        self.vpd_scatter_ref = None
        self.debug_ref = None
        self.csv_viewer_ref = None
        self.cam_viewer_ref = None
        self.device_picker_ref = None
        self.sensor_mixed_mode_ref = None
        self.grow_rooms_ref = None  # 🔥 HIER init
        self.mixed_mode_active = False
        self.mixed_selected_buffers = set()
        self.mixed_device_modes = {}
        # Aktives Gerät (Index)
        self.active_index = 0
        self.active_channel = "adv"
        # LED Status
        self.led_state = {"alive": False, "status": "offline"}

        self.rssi_history = {}  # MUSS ein Dictionary sein, keine Liste []
        self.max_history = config.get_tile_graph_window()
        self._last_frame_time = 0  # NEU für Ratenberechnung
        self.current_latency = 0   # NEU

        # Heartbeat
        self._last_state = {}
        self.trend_window = config.get_tile_graph_window() 
        self._trend_buffers = {}
        self.global_trends = {}
        # Global Tick
        # Statt 0.5 nehmen wir den Wert aus der Config
        self._main_tick = Clock.schedule_interval(self._global_update, config.get_refresh_interval())
        self.graph_buffers = {} # Hier speichern wir die Historie: { "MAC_temp_in": [22.1, 22.2, ...] }
        self._last_smoothed_values = {} # Merker für globales Smoothing
        self.smoothing_factor = 0.1     # Zentraler Glättungsfaktor
        self.unit_map = {}  # Speichert { "MAC_adv_temp_in": "°F" }
        self.broadcast_active = True
        self.broadcast_data_available = True
        self.broadcast_data_available = self._check_mixed_file()

    def set_active_channel(self, channel):
        if channel not in ("adv", "gatt"):
            return
    
        if channel == self.active_channel:
            return
    
        prev = self.active_channel
        self.active_channel = channel
        self._last_counter = None
    
        print(f"[GSM] Channel -> {channel}")
    
        try:
            import core
            import config
    
            item = self.get_device_list()[self.active_index]
            device_id = item.get("device_id") if isinstance(item, dict) else item
    
            cfg = config._init()
            dev = cfg.get("devices", {}).get(device_id, {})
            bridge_profile = dev.get("bridge_profile", "")
    
            # -----------------------------------------
            # ADV → GATT
            # -----------------------------------------
            if prev == "adv" and channel == "gatt":
                if bridge_profile:
                    self.write_gatt_bridge_config(device_id)
                    core.restart_gatt_bridge()
    
            # -----------------------------------------
            # GATT → ADV
            # -----------------------------------------
            elif prev == "gatt" and channel == "adv":
                pass
                #core.restart_adv_bridge()
    
        except Exception as e:
            print("[GSM] channel switch failed:", e)
    
    def get_active_channel(self):
        return self.active_channel
    
    # ---------------------------------------------------------
    # PUBLIC API – Device Switch
    # ---------------------------------------------------------
    def set_active_index(self, idx):
        idx = max(0, int(idx))
    
        if idx == self.active_index:
            return
    
        self.active_index = idx
        self._last_counter = None
    
        print(f"[GSM] Active device -> {idx}")
    
        try:
            import core
            import config
    
            item = self.get_device_list()[self.active_index]
            device_id = item.get("device_id") if isinstance(item, dict) else item
    
            # -----------------------------------------
            # ADV: Gerät gewechselt → ADV restart
            # -----------------------------------------
            if self.active_channel == "adv":
                pass   # ⛔ ADV bewusst NICHT neu starten
                #core.restart_adv_bridge()
    
            # -----------------------------------------
            # GATT: Gerät gewechselt → Config + GATT restart
            # -----------------------------------------
            elif self.active_channel == "gatt":
                cfg = config._init()
                dev = cfg.get("devices", {}).get(device_id, {})
                bridge_profile = dev.get("bridge_profile", "")
    
                if bridge_profile:
                    self.write_gatt_bridge_config(device_id)
                    core.restart_gatt_bridge()
    
        except Exception as e:
            print("[GSM] device switch failed:", e)
    
        # Header sofort aktualisieren
        data = BUFFER.get()
        if isinstance(data, list) and len(data) > idx:
            frame = data[idx]
                
    def get_device_list(self):
        import config
        cfg = config._init()
        devs = cfg.get("devices", {})
        if not isinstance(devs, dict):
            return []
        return list(devs.keys())
    def get_device_label(self, device_id):
        import config
        cfg = config._init()
        d = cfg.get("devices", {}).get(device_id, {})
        name = d.get("name")
        return name if name else device_id        
####
    # ---------------------------------------------------------
    # Screen Attach
    # ---------------------------------------------------------
    def attach_dashboard(self, scr):
        self.dashboard_ref = scr
    
        try:
            import config
            import core
    
            cfg = config._init()
            devices = cfg.get("devices", {})
    
            if not devices:
                return
    
            device_ids = list(devices.keys())
            self.active_index = 0
            device_id = device_ids[0]
    
            dev = devices.get(device_id, {})
            bridge_profile = dev.get("bridge_profile")
    
            if bridge_profile:
                self.write_gatt_bridge_config(device_id)
                core.restart_bridge()
                self.active_channel = "gatt"
            else:
                pass
                #core.restart_adv_bridge()
                self.active_channel = "adv"
    
            print(f"[GSM] Bootstrap device={device_id} channel={self.active_channel}")
    
        except Exception as e:
            print("[GSM] Bootstrap failed:", e)

    def attach_fullscreen(self, scr):
        self.fullscreen_ref = scr
    def attach_setup(self, scr):
        self.setup_ref = scr
    def attach_about(self, scr):
        self.about_ref = scr
    def attach_settings(self, scr):
        self.settings_ref = scr
    def attach_vpd_scatter(self, scr):
        self.vpd_scatter_ref = scr
    def attach_debug(self, scr):
        self.debug_ref = scr
    def attach_csv_viewer(self, scr):
        self.csv_viewer_ref = scr
    def attach_cam_viewer(self, scr):
        self.cam_viewer_ref = scr        
    def attach_device_picker(self, scr):
        self.device_picker_ref = scr
    def attach_sensor_mixed_mode(self, scr):
        self.sensor_mixed_mode_ref = scr
    def attach_grow_rooms(self, scr):
        self.grow_rooms_ref = scr
####
    # ---------------------------------------------------------
    # ZENTRALE GRAPHEN, SMOOTHING & TREND-FABRIK 
    # ---------------------------------------------------------
    def process_new_value(self, key, value):
        if value is None: return
        try:
            val_float = float(value)
            
            if key not in self._last_smoothed_values:
                smoothed = val_float
            else:
                last = self._last_smoothed_values[key]
                # DRIFT-CHECK: Wenn der Sprung riesig ist (> 5°C), Smoothing ignorieren
                if abs(val_float - last) > 5.0:
                    smoothed = val_float
                else:
                    f = self.smoothing_factor
                    smoothed = (last * (1 - f)) + (val_float * f)
            
            self._last_smoothed_values[key] = smoothed
            
            # Puffer befüllen (Graph & Trend)


            # 1. Trend-Buffer (für die Pfeile)
            if key not in self._trend_buffers: 
                self._trend_buffers[key] = []
            
            t_buf = self._trend_buffers[key]
            t_buf.append(smoothed)
            
            if len(t_buf) > self.trend_window: 
                t_buf.pop(0)
            
            # 2. Graphen-Historie speichern
            if key not in self.graph_buffers:
                self.graph_buffers[key] = []
            
            g_buf = self.graph_buffers[key]
            g_buf.append(smoothed)
            
            if len(g_buf) > self.max_history:
                g_buf.pop(0)
                
            # 3. Trend berechnen
            self.global_trends[key] = self._calculate_trend_logic(t_buf)
            
        except Exception as e:
            print(f"[GSM] Error in process_new_value: {e}")

    def get_graph_data(self, key):
        """Liefert die Historie für einen Screen (z.B. Fullscreen)"""
        return self.graph_buffers.get(key, [])

    def _calculate_trend_logic(self, buf):
        """Die mathematische Wahrheit - nur hier wird entschieden!"""
        if len(buf) < 5: 
            return 0 # Nicht genug Daten -> Stabil/Neutral
            
        # Wir vergleichen das Ende mit dem Anfang des Buffers
        start = buf[0]
        end = buf[-1]
        diff = end - start
        
        # Dynamischer Schwellenwert (0.2% vom Wert, mind. 0.01)
        threshold = max(0.01, abs(start) * 0.002)
        
        if diff > threshold:
            return 1   # Steigend
        elif diff < -threshold:
            return -1  # Fallend
        return 0       # Stabil

    def get_trend_icon(self, key):
        val = self.global_trends.get(key, 0)
        # NUR der nackte Hex-Code, KEIN Markup hier!
        icons = {-1: "\uf063", 1: "\uf062", 0: "\uf061"}
        return icons[val]
####
    # ---------------------------------------------------------
    # UNIT RESOLVER (für Tiles + Fullscreen)
    # ---------------------------------------------------------
    
    def get_unit(self, key):
        """Gibt die Einheit zurück, die zuletzt aus dem BUFFER gelesen wurde."""
        return self.unit_map.get(key, "")

    def toggle_temp_unit(self):
        old_unit = getattr(self, "temp_unit", "°C")
        new_unit = "°F" if old_unit == "°C" else "°C"
        self.temp_unit = new_unit
        
        # RE-CALC BUFFER: Verhindert den visuellen Drift im Graphen
        for key in self.graph_buffers:
            if "temp" in key:
                if new_unit == "°F": # C -> F
                    self.graph_buffers[key] = [(v * 9/5) + 32 for v in self.graph_buffers[key]]
                    if key in self._last_smoothed_values:
                        self._last_smoothed_values[key] = (self._last_smoothed_values[key] * 9/5) + 32
                else: # F -> C
                    self.graph_buffers[key] = [(v - 32) * 5/9 for v in self.graph_buffers[key]]
                    if key in self._last_smoothed_values:
                        self._last_smoothed_values[key] = (self._last_smoothed_values[key] - 32) * 5/9
        print(f"[GSM] Unit switched to {new_unit}, Buffers converted.")
####
    # ---------------------------------------------------------
    # LED Helpers
    # ---------------------------------------------------------
    def _push_led(self):
        if self.dashboard_ref:
            self.dashboard_ref.header.set_led(self.led_state)
        if self.fullscreen_ref:
            self.fullscreen_ref.header.set_led(self.led_state)
        if self.setup_ref:
            self.setup_ref.header.set_led(self.led_state)
        if self.about_ref:
            self.about_ref.header.set_led(self.led_state)
        if self.settings_ref:
            self.settings_ref.header.set_led(self.led_state)
        if self.vpd_scatter_ref:
            self.vpd_scatter_ref.header.set_led(self.led_state)
        if self.debug_ref:
            self.debug_ref.header.set_led(self.led_state)
        if self.csv_viewer_ref:
            self.csv_viewer_ref.header.set_led(self.led_state)            
        if self.cam_viewer_ref:
            self.cam_viewer_ref.header.set_led(self.led_state)            
        if self.device_picker_ref:
            self.device_picker_ref.header.set_led(self.led_state)
        if self.sensor_mixed_mode_ref:
            self.sensor_mixed_mode_ref.header.set_led(self.led_state)
        if self.grow_rooms_ref:                # 🔥 NEU: GrowRooms exakt wie alle anderen
            self.grow_rooms_ref.header.set_led(self.led_state)

    def _led_offline(self):
        self.led_state = {"alive": False, "status": "offline"}
        self._push_led()

    def _led_nodata(self):
        self.led_state = {"alive": False, "status": "nodata"}
        self._push_led()

    def _led_stale(self):
        self.led_state = {"alive": True, "status": "stale"}
        self._push_led()

    def _led_flow(self):
        self.led_state = {"alive": True, "status": "flow"}
        self._flow_hold = True
        self._last_packet_timestamp = time.time()  # 🔥 NEU: Zeitstempel beim Puls merken
        self._push_led()
####
    # ---------------------------------------------------------
    # Drei-Gestirn (Start / Stop / Reset)
    # ---------------------------------------------------------
    def start(self):
        print("[STATE] START")
        self.running = True
        self._led_offline()
        self._refresh_all_buttons()

    def stop(self):
        print("[STATE] STOP")
        self.running = False
        # Wir halten den Puls an
        self._led_offline()
        self._last_counter = None
        self._refresh_all_buttons()

    def reset(self):
        """ Radikaler Kahlschlag - alles auf Null, ohne Haken. """
        print("[GSM] GLOBAL RESET - Aufräumen gestartet...")
        
        # 1. Alles stoppen & Timer entkoppeln
        self._led_offline()
        self._last_counter = None
        self._last_raw = None
        
        # 2. Dicts LEEREN (nicht löschen, nur Inhalt weg)
        self.graph_buffers.clear() 
        self.rssi_history.clear() 
        self._trend_buffers.clear()
        self.global_trends.clear()
        self._last_smoothed_values.clear()

        # 3. Den Hardware-Input-Buffer leeren (Falls vorhanden)
        if hasattr(BUFFER, 'clear'):
            BUFFER.clear()

        # 4. DIE SCREENS BENACHRICHTIGEN
        for screen_ref in [self.dashboard_ref, self.fullscreen_ref, self.vpd_scatter_ref]:
            if screen_ref and hasattr(screen_ref, "reset_from_global"):
                # Wir nutzen Clock, damit der Screen-Reset NICHT den GSM blockiert
                Clock.schedule_once(lambda dt, s=screen_ref: s.reset_from_global(), 0)

        print("[GSM] System ist jetzt klinisch rein.")
    # ---------------------------------------------------------
    # Button Sync
    # ---------------------------------------------------------
    def _refresh_all_buttons(self):
        if self.dashboard_ref and hasattr(self.dashboard_ref, "controls"):
            self.dashboard_ref.controls.refresh_state(self.running)
    
        if self.fullscreen_ref and hasattr(self.fullscreen_ref, "controls"):
            self.fullscreen_ref.controls.refresh_state(self.running)
    
        if self.vpd_scatter_ref and hasattr(self.vpd_scatter_ref, "controls"):
            self.vpd_scatter_ref.controls.refresh_state(self.running)

    def bind_screen_manager(self, sm):
        self.screen_manager = sm


    # ---------------------------------------------------------
    # GLOBAL UPDATE TICK!!!
    # ---------------------------------------------------------
    def _global_update(self, dt):
        BUFFER.soft_reload()
        data = BUFFER.get()
    
        if not self.running or not data or not isinstance(data, list):
            self._led_nodata()
            return
        # --- NEU: MIXED MODE LOGIK AKTIVIEREN ---
        if self.mixed_mode_active:
            # Berechnet Durchschnitte und schreibt data/mixed.json
            self._update_mixed_logic(data)    

        # 1. Aktives Gerät und Kanal bestimmen
        idx = min(self.active_index, len(data)-1)
        d = data[idx]
        dev_id = d.get("device_id")
        ch_name = self.active_channel  # "adv" oder "gatt"
        ch = d.get(ch_name, {})
        
        if not isinstance(ch, dict):
            self._led_offline()
            return

        # 2. Metriken UND Einheiten direkt aus dem BUFFER-Knoten ziehen
        metrics_to_process = {
            "temp_in": ch.get("internal", {}).get("temperature"),
            "hum_in":  ch.get("internal", {}).get("humidity"),
            "vpd_in":  ch.get("vpd_internal"),
            "temp_ex": ch.get("external", {}).get("temperature"),
            "hum_ex":  ch.get("external", {}).get("humidity"),
            "vpd_ex":  ch.get("vpd_external"),
        }

        for m_name, node in metrics_to_process.items():
            if isinstance(node, dict) and node.get("value") is not None:
                val = node.get("value")
                unit = node.get("unit", "")
                key = f"{dev_id}_{ch_name}_{m_name}"
                
                # Wert glätten und in Historie speichern
                self.process_new_value(key, val)
                
                # EINHEIT IM GSM MERKEN (für get_unit)
                if not hasattr(self, "unit_map"): self.unit_map = {}
                self.unit_map[key] = unit
        # ---------------------------------------------------------
        # VPD COORDINATES
        # ---------------------------------------------------------
        coord = ch.get("coord", {})
        
        coord_internal = coord.get("internal", {})
        coord_external = coord.get("external", {})
        
        coord_metrics = {
            "vpd_x_in": coord_internal.get("x"),
            "vpd_y_in": coord_internal.get("y"),
            "vpd_x_ex": coord_external.get("x"),
            "vpd_y_ex": coord_external.get("y"),
        }
        
        for m_name, val in coord_metrics.items():
            if val is not None:
                key = f"{dev_id}_{ch_name}_{m_name}"
        
                self.process_new_value(key, val)
        
                if not hasattr(self, "unit_map"):
                    self.unit_map = {}
        
                self.unit_map[key] = ""
                
        # 3. MAC/ID für die UI vorbereiten
        mac = _extract_mac(dev_id)
        d["device_id_flat"] = mac
        
        # 5. UI-Update (Screen Manager)
        if hasattr(self, 'screen_manager'):
            current_scr = self.screen_manager.get_screen(self.screen_manager.current)
            if hasattr(current_scr, 'update_from_global'):
                # Wir geben das aufbereitete Paket weiter
                current_scr.update_from_global({
                    "device_id": dev_id,
                    "device_id_flat": mac,
                    "channel": ch_name,
                    ch_name: ch,
                    "_active_keys": self.extract_active_keys(d)
                })
        # ---------------------------------------------------------
        # ALIVE / COUNTER / LED AUF BASIS DES AKTIVEN KANALS
        # ---------------------------------------------------------
        if not isinstance(ch, dict):
            # Channel existiert nicht → echtes OFFLINE
            self._led_offline()
            return
    
        alive = ch.get("alive", False)
        
        # RSSI extrahieren und GERÄTESPEZIFISCH speichern
        try:
            current_rssi = d.get("health", {}).get("signal", {}).get("rssi")
            if current_rssi is not None and dev_id:
                # Sicherstellen, dass rssi_history ein Dict ist
                if not isinstance(self.rssi_history, dict):
                    self.rssi_history = {}
        
                # Device-Eintrag anlegen, falls nicht existent
                if dev_id not in self.rssi_history:
                    self.rssi_history[dev_id] = []
        
                # Wert einfügen
                hist = self.rssi_history[dev_id]
                hist.append(float(current_rssi))
        
                # Länge begrenzen
                if len(hist) > self.max_history:
                    hist.pop(0)
        except:
            pass

        counter = ch.get("packet_counter")
        raw = ch.get("raw") or ch.get("adv_raw") or ch.get("gat_raw")
        
        if not alive:
            self._led_offline()
            self._last_counter = None
            self._last_raw = None
        
        else:
            # -------------------------
            # ADV → RAW-basierter Puls
            # -------------------------
            if ch_name == "adv":
                if raw and raw != getattr(self, "_last_raw", None):
                    self._led_flow()
                else:
                    if self._flow_hold:
                        self._flow_hold = False
                    else:
                        self._led_stale()
                self._last_raw = raw
        
            # -------------------------
            # GATT → Counter-basierter Puls
            # -------------------------
            else:
                if counter is None:
                    self._led_stale()
                else:
                    if self._last_counter is None:
                        self._led_stale()
                    elif counter != self._last_counter:
                        self._led_flow()
                    else:
                        if self._flow_hold:
                            self._flow_hold = False
                        else:
                            self._led_stale()
                    self._last_counter = counter
    
        if not self.running:
            return
    
        # ---------------------------------------------------------
        # ACTIVE KEYS → Kanalbasis
        # ---------------------------------------------------------
        d["_active_keys"] = self.extract_active_keys(d)
    
        # ---------------------------------------------------------
        # SCREEN UPDATES!!!
        # Dem Screen geben wir nur den aktiven Kanal
        # ---------------------------------------------------------
        
        out = {
            "device_id": d.get("device_id"),
            "device_id_flat": d.get("device_id_flat"),
            "channel": ch_name,
            ch_name: ch,
            "adv": d.get("adv"),
            "gatt": d.get("gatt"),
            "bridge_alive": d.get("bridge_alive"),
            "bridge_status": d.get("bridge_status"),
            "health": d.get("health"),
            "_active_keys": d["_active_keys"],
        }
    
        # 2. NUR den Screen updaten, den der User gerade sieht!
        if hasattr(self, 'screen_manager'):
            current_screen_name = self.screen_manager.current
            current_screen_obj = self.screen_manager.get_screen(current_screen_name)
            
            # Hat der aktuelle Screen eine Update-Funktion? Dann feuer frei!
            if hasattr(current_screen_obj, 'update_from_global'):
                current_screen_obj.update_from_global(out)
 
 ####
    # ---------------------------------------------------------
    # Active Keys – MULTI-CHANNEL (adv + gatt, ohne Vorrang) MIXED MODE
    # ---------------------------------------------------------
    def extract_active_keys(self, d):
        active = set()

        # Neuer Multi-Channel-Pfad: adv / gatt
        for ch_name in ("adv", "gatt"):
            ch = d.get(ch_name)
            if not isinstance(ch, dict):
                continue

            internal = ch.get("internal", {})
            external = ch.get("external", {})
            vpd_int = ch.get("vpd_internal", {})
            vpd_ext = ch.get("vpd_external", {})

            # interne Werte
            if internal.get("temperature", {}).get("value") is not None:
                active.add("temp_in")
            if internal.get("humidity", {}).get("value") is not None:
                active.add("hum_in")
            if vpd_int.get("value") is not None:
                active.add("vpd_in")

            # externe Werte
            if external.get("present"):
                if external.get("temperature", {}).get("value") is not None:
                    active.add("temp_ex")
                if external.get("humidity", {}).get("value") is not None:
                    active.add("hum_ex")
                if vpd_ext.get("value") is not None:
                    active.add("vpd_ex")

        return list(active)

####
    # ---------------------------------------------------------
    # GATT BRIDGE CONFIG (Bridge-only, Header-triggered)
    # ---------------------------------------------------------
    def write_gatt_bridge_config(self, device_id):
        import json
        import config
        import os
    
        cfg = config._init()
        dev = cfg.get("devices", {}).get(device_id)
    
        if not dev:
            print(f"[GSM] Kein Device in config: {device_id}")
            return
    
        bridge_profile = dev.get("bridge_profile", "")
        if not bridge_profile:
            print(f"[GSM] Kein bridge_profile für {device_id}")
            return
    
        gatt_cfg = {
            "devices": {
                device_id: {
                    "bridge_profile": bridge_profile
                }
            }
        }
    
        path = os.path.join(config.DATA, "gatt_config.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(gatt_cfg, f, indent=2)
    
        print(f"[GSM] gatt_config.json geschrieben für {device_id}")

####
    # ---------------------------------------------------------
    # Mixed Mode 
    # ---------------------------------------------------------

    def set_mixed_mode(self, state: bool):
        self.mixed_mode_active = state
    
    def toggle_mixed_buffer(self, buf_key):
        if buf_key in self.mixed_selected_buffers:
            self.mixed_selected_buffers.remove(buf_key)
        else:
            self.mixed_selected_buffers.add(buf_key)

    def get_mixed_mode(self, dev_id):
        return self.mixed_device_modes.get(str(dev_id), "mixed")
    
    def set_mixed_mode_for_device(self, dev_id, mode):
        self.mixed_device_modes[str(dev_id)] = mode

    def _update_mixed_logic(self, all_data):
        """Berechnet die Mittelwerte für das gesamte System im Hintergrund."""
        selected = self.mixed_selected_buffers
        if not selected or not all_data:
            self._write_mixed_json([]) # Leeren wenn nichts gewählt
            return

        averaging_map = {"temp": [], "hum": [], "vpd": [], "dew": []}
        active_device_ids = []

        for frame in all_data:
            dev_id = str(frame.get("device_id"))
            if dev_id not in selected:
                continue
            
            # Welche Modi sind für dieses Gerät aktiv? (Internal/External)
            active_modes = self.mixed_device_modes.get(dev_id, {"internal"})
            
            for ch_name in ("adv", "gatt"):
                ch = frame.get(ch_name)
                if not isinstance(ch, dict): continue

                for mode in active_modes:
                    vals = ch.get(mode)
                    if not isinstance(vals, dict): continue

                    # Werte sammeln
                    t = vals.get("temperature", {}).get("value")
                    h = vals.get("humidity", {}).get("value")
                    if t is not None: averaging_map["temp"].append(float(t))
                    if h is not None: averaging_map["hum"].append(float(h))

                    # VPD & Dew Point
                    v_key = f"vpd_{mode}"
                    d_key = f"dew_point_{mode}"
                    v = ch.get(v_key, {}).get("value")
                    d = ch.get(d_key, {}).get("value")
                    if v is not None: averaging_map["vpd"].append(float(v))
                    if d is not None: averaging_map["dew"].append(float(d))
            
            active_device_ids.append(dev_id)
        results = {}
        has_real_data = False # Tracker, ob wir wirklich Zahlen haben

        for key, vals in averaging_map.items():
            if vals:
                avg = sum(vals) / len(vals)
                results[key] = avg
                self.process_new_value(f"mixed_avg_{key}", avg)
                has_real_data = True # Wir haben mindestens einen echten Mittelwert
            else:
                results[key] = None

        # WICHTIG: Wenn keine echten Daten da sind, schreiben wir eine leere Liste
        if not has_real_data:
            self._write_mixed_json([]) 
            return []

        self._write_mixed_json(results, active_device_ids)
        return results
        # Mittelwerte berechnen
        results = {}
        for key, vals in averaging_map.items():
            if vals:
                avg = sum(vals) / len(vals)
                results[key] = avg
                # Trends direkt im GSM füttern!
                self.process_new_value(f"mixed_avg_{key}", avg)
            else:
                results[key] = None

        self._write_mixed_json(results, active_device_ids)
        return results

    def _write_mixed_json(self, results, device_ids=None):
        import json, os
        from datetime import datetime
        from dashboard_gui.global_state_manager import GLOBAL_STATE
    
        path = os.path.join("data", "mixed.json")
    
        # -------------------------
        # FALL 1: KEINE DATEN
        # -------------------------
        if not results:
            with open(path, "w") as f:
                json.dump([], f)
    
            GLOBAL_STATE.broadcast_data_available = False
    
            if GLOBAL_STATE.broadcast_active:
                GLOBAL_STATE.broadcast_active = False
                try:
                    import core
                    core.stop_broadcast_bridge()
                except:
                    pass
    
            # 🔥 ZWINGEND UI REFRESH
            GLOBAL_STATE.refresh_all_headers()
            return
    
        # -------------------------
        # FALL 2: DATEN VORHANDEN
        # -------------------------
        json_data = [{
            "timestamp": datetime.now().isoformat(),
            "avg_temp": results.get("temp"),
            "avg_hum": results.get("hum"),
            "avg_vpd": results.get("vpd"),
            "avg_dew": results.get("dew"),
            "devices": device_ids
        }]
    
        with open(path, "w") as f:
            json.dump(json_data, f, indent=2)
    
        GLOBAL_STATE.broadcast_data_available = True
    
        # 🔥 Wichtig: KEIN automatisches Einschalten
        GLOBAL_STATE.refresh_all_headers()

    def _check_mixed_file(self):
        import os, json
    
        path = os.path.join("data", "mixed.json")
    
        if not os.path.exists(path):
            return False
    
        try:
            with open(path, "r") as f:
                data = json.load(f)
                return bool(data)
        except:
            return False
    def refresh_all_headers(self):
        for ref in [
            self.dashboard_ref,
            self.fullscreen_ref,
            self.vpd_scatter_ref,
            self.setup_ref,
            self.settings_ref,
            self.debug_ref,
            self.csv_viewer_ref,
            self.cam_viewer_ref,
            self.sensor_mixed_mode_ref,
            self.grow_rooms_ref,
        ]:
            if ref and hasattr(ref, "header"):
                ref.header.refresh_broadcast_state()

    # ---------------------------------------------------------
    # Config Refresh/Reload
    # ---------------------------------------------------------
    def refresh_config(self):
        import config
        from kivy.clock import Clock
    
        # ---------------------------------
        # Fenster übernehmen
        # ---------------------------------
        self.trend_window = config.get_tile_graph_window()
        self.max_history = self.trend_window
    
        # ---------------------------------
        # TREND BUFFER trimmen
        # ---------------------------------
        for key in self._trend_buffers:
            buf = self._trend_buffers[key]
            if len(buf) > self.trend_window:
                self._trend_buffers[key] = buf[-self.trend_window:]
    
        # ---------------------------------
        # GRAPH BUFFER trimmen (FEHLTE!)
        # ---------------------------------
        for key in self.graph_buffers:
            buf = self.graph_buffers[key]
            if len(buf) > self.max_history:
                self.graph_buffers[key] = buf[-self.max_history:]
    
        # ---------------------------------
        # RSSI BUFFER trimmen (FEHLTE!)
        # ---------------------------------
        for dev in self.rssi_history:
            buf = self.rssi_history[dev]
            if len(buf) > self.max_history:
                self.rssi_history[dev] = buf[-self.max_history:]
    
        # ---------------------------------
        # GLOBAL UPDATE INTERVAL
        # ---------------------------------
        new_interval = config.get_refresh_interval()
    
        if hasattr(self, "_main_tick"):
            self._main_tick.cancel()
    
        self._main_tick = Clock.schedule_interval(self._global_update, new_interval)
    
        print(f"[GSM] LIVE-SYNC: Fenster={self.trend_window}, Intervall={new_interval}s")

GLOBAL_STATE = GlobalStateManager()
