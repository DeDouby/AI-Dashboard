# dashboard_gui/global_state_manager.py
# HEARTBEAT + MULTI-DEVICE – CLEAN VERSION

from kivy.clock import Clock
from dashboard_gui.data_buffer import BUFFER


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
        self.mixed_mode_active = False
        self.mixed_selected_buffers = set()
        # Aktives Gerät (Index)
        self.active_index = 0
        self.active_channel = "adv"
        # LED Status
        self.led_state = {"alive": False, "status": "offline"}


        # Heartbeat
        self._last_state = {}

        # Global Tick
        Clock.schedule_interval(self._global_update, 0.5)



    def set_active_channel(self, channel):
        if channel not in ("adv", "gatt"):
            return
    
        # nichts tun, wenn gleich
        if channel == self.active_channel:
            return
    
        prev = self.active_channel
        self.active_channel = channel
        self._last_counter = None
    
        print(f"[GSM] Channel -> {channel}")
    
        # -----------------------------------------
        # 🔥 ADV → GATT: Config schreiben + Restart
        # -----------------------------------------
        if prev == "adv" and channel == "gatt":
            try:
                import config
                import core
    
                item = self.get_device_list()[self.active_index]
                device_id = item.get("device_id") if isinstance(item, dict) else item
    
                cfg = config._init()
                dev = cfg.get("devices", {}).get(device_id, {})
                bridge_profile = dev.get("bridge_profile", "")
    
                if bridge_profile:
                    self.write_gatt_bridge_config(device_id)
                    core.restart_bridge()
    
            except Exception as e:
                print("[GSM] adv→gatt switch failed:", e)
    
    def get_active_channel(self):
        return self.active_channel
    
    # ---------------------------------------------------------
    # PUBLIC API – Device Switch
    # ---------------------------------------------------------

    def set_active_index(self, idx):
        idx = int(idx)
        if idx < 0:
            idx = 0
    
        # nichts tun, wenn gleiches Gerät
        if idx == self.active_index:
            return
    
        self.active_index = idx
    
        # -----------------------------------------
        # 🔥 IMMER Bridge restart bei Device-Wechsel
        # -----------------------------------------
        try:
            import core
            core.restart_bridge()
        except Exception as e:
            print("[GSM] bridge restart failed:", e)
    
        # -----------------------------------------
        # 🔧 GATT: zusätzlich Config schreiben
        # -----------------------------------------
        if self.active_channel == "gatt":
            try:
                import config
    
                item = self.get_device_list()[self.active_index]
                device_id = item.get("device_id") if isinstance(item, dict) else item
    
                cfg = config._init()
                dev = cfg.get("devices", {}).get(device_id, {})
                bridge_profile = dev.get("bridge_profile", "")
    
                if bridge_profile:
                    self.write_gatt_bridge_config(device_id)
    
            except Exception as e:
                print("[GSM] auto-gatt switch failed:", e)
    
        self._last_counter = None
        print(f"[GSM] Active device -> {idx}")
    
        # Header sofort aktualisieren
        data = BUFFER.get()
        if isinstance(data, list) and len(data) > idx:
            frame = data[idx]
    
            if self.dashboard_ref:
                self.dashboard_ref.header.set_device_label(frame)
            if self.fullscreen_ref:
                self.fullscreen_ref.header.set_device_label(frame)
            if self.setup_ref:
                self.setup_ref.header.set_device_label(frame)
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
    # ---------------------------------------------------------
    # Screen Attach
    # ---------------------------------------------------------
    def attach_dashboard(self, scr):
        self.dashboard_ref = scr
    
        # -------------------------------------------------
        # BOOTSTRAP: aktives Device + Channel + Bridge
        # -------------------------------------------------
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
                self.set_active_channel("gatt")
            else:
                self.set_active_channel("adv")
    
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
        self._push_led()

    # ---------------------------------------------------------
    # Drei-Gestirn
    # ---------------------------------------------------------
    def start(self):
        print("[STATE] START")
        self.running = True
        self._led_offline()
        self._refresh_all_buttons()

    def stop(self):
        print("[STATE] STOP")
        self.running = False
        self._led_offline()
        self._last_counter = None
        self._refresh_all_buttons()

    def reset(self):
        print("[STATE] RESET")
        self._led_offline()
        self._last_counter = None
        self._refresh_all_buttons()
    
        if self.dashboard_ref:
            self.dashboard_ref.reset_from_global()
        if self.fullscreen_ref:
            self.fullscreen_ref.reset_from_global()
        if self.vpd_scatter_ref:
            self.vpd_scatter_ref.reset_from_global()
    # ---------------------------------------------------------
    # GLOBAL TICK
    # ---------------------------------------------------------
    def _global_update(self, dt):
        BUFFER.soft_reload()
        data = BUFFER.get()
    
        if not self.running:
            return
    
        if not data or not isinstance(data, list):
            self._led_nodata()
            return
    
        # aktives Gerät clampen
        idx = min(self.active_index, len(data)-1)
        d = data[idx]
    
        # aktiver Kanal
        ch_name = self.active_channel           # "adv" oder "gatt"
        ch = d.get(ch_name)                     # der gewählte Stream
        dev_id = d.get("device_id")
        

        # MAC flatten
        mac = _extract_mac(d.get("device_id"))
        d["device_id"] = mac
        d["device_id_flat"] = mac
    
        # ---------------------------------------------------------
        # ALIVE / COUNTER / LED AUF BASIS DES AKTIVEN KANALS
        # ---------------------------------------------------------
        if not isinstance(ch, dict):
            # Channel existiert nicht → echtes OFFLINE
            self._led_offline()
            return
    
        alive = ch.get("alive", False)
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
        # SCREEN UPDATES (Dashboard & Fullscreen)
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
    
        if self.dashboard_ref:
            self.dashboard_ref.update_from_global(out)
        if self.fullscreen_ref:
            self.fullscreen_ref.update_from_global(out)
        if self.setup_ref:
            self.setup_ref.update_from_global(out)
        if self.about_ref:
            self.about_ref.update_from_global(out)            
        if self.settings_ref:
            self.settings_ref.update_from_global(out) 
        if self.vpd_scatter_ref:
            self.vpd_scatter_ref.update_from_global(out)
        if self.debug_ref:
            self.debug_ref.update_from_global(out)            
        if self.csv_viewer_ref:
            self.csv_viewer_ref.update_from_global(out)
        if self.cam_viewer_ref:
            self.cam_viewer_ref.update_from_global(out)            
        if self.device_picker_ref:
            self.device_picker_ref.update_from_global(out)
        if self.sensor_mixed_mode_ref:
            self.sensor_mixed_mode_ref.update_from_global(out)
    # ---------------------------------------------------------
    # Active Keys – MULTI-CHANNEL (adv + gatt, ohne Vorrang)
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

        # Fallback für ALTEN Single-Channel-Frame (falls mal nötig)
        if not active and "internal" in d:
            internal = d.get("internal", {})
            external = d.get("external", {})
            vpd_int = d.get("vpd_internal", {})
            vpd_ext = d.get("vpd_external", {})

            if internal.get("temperature", {}).get("value") is not None:
                active.add("temp_in")
            if internal.get("humidity", {}).get("value") is not None:
                active.add("hum_in")
            if vpd_int.get("value") is not None:
                active.add("vpd_in")

            if external.get("present"):
                if external.get("temperature", {}).get("value") is not None:
                    active.add("temp_ex")
                if external.get("humidity", {}).get("value") is not None:
                    active.add("hum_ex")
                if vpd_ext.get("value") is not None:
                    active.add("vpd_ex")

        return list(active)

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

    def set_mixed_mode(self, state: bool):
        self.mixed_mode_active = state
    
    def toggle_mixed_buffer(self, buf_key):
        if buf_key in self.mixed_selected_buffers:
            self.mixed_selected_buffers.remove(buf_key)
        else:
            self.mixed_selected_buffers.add(buf_key)
    # ---------------------------------------------------------
    # APPLY NEW CONFIG – globaler Refresh
    # ---------------------------------------------------------
    def apply_new_config(self):
        import config
        import decoder
        from kivy.app import App

        print("[GSM] Neue Config wird angewendet…")

        # 1) Config reload
        try:
            if hasattr(config, "reload"):
                config.reload()
            else:
                config.load()
            print("[GSM] Config reloaded.")
        except Exception as e:
            print("[GSM] Fehler beim Config-Reload:", e)

        # 2) Decoder weicher Reset (keine Threads zerstören)
        try:
            if hasattr(decoder, "UPTIME_START"):
                decoder.UPTIME_START = None
            print("[GSM] Decoder soft-synced.")
        except Exception as e:
            print("[GSM] Decoder-Sync Fehler:", e)

        # 3) Screens refreshen (nur wenn vorgesehen)
        app = App.get_running_app()
        if not app:
            return

        sm = app.sm  # kommt aus deiner main.py

        for screen_name in [
            "dashboard",
            "fullscreen",
            "device_picker",
            "debug",
            "filemanager",
            "setup"
        ]:
            try:
                scr = sm.get_screen(screen_name)
                if hasattr(scr, "refresh_after_config"):
                    scr.refresh_after_config()
                    print(f"[GSM] {screen_name} refreshed.")
            except:
                pass

        print("[GSM] Config vollständig aktiviert.")


GLOBAL_STATE = GlobalStateManager()
