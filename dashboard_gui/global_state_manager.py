# dashboard_gui/global_state_manager.py
# HEARTBEAT + MULTI-DEVICE – CLEAN VERSION

from kivy.clock import Clock
from dashboard_gui.data_buffer import BUFFER
import time
import config
from dashboard_gui.engines.graph_engine import GraphEngine
from dashboard_gui.engines.ui_manager import UIManager # oben importieren
from dashboard_gui.engines.config_engine import ConfigEngine# oben importieren
from dashboard_gui.engines.led_engine import LedEngine
from dashboard_gui.engines.mixed_engine import MixedEngine
from dashboard_gui.engines.metrics_engine import MetricsEngine
from dashboard_gui.engines.gatt_config_engine import GattConfigEngine
from dashboard_gui.engines.active_channel_engine import init_active_channel_engine
from dashboard_gui.engines.unit_engine import UnitEngine
from dashboard_gui.engines.swipe_gesture_engine import SwipeGestureEngine
# Initialisieren
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


        # Mixed Mode
        self.mixed_mode_active = False
        self.mixed_selected_buffers = set()
        self.mixed_device_modes = {}
        # Aktives Gerät (Index)

        # LED Status

        self.rssi_history = {}  # MUSS ein Dictionary sein, keine Liste []
        self.max_history = config.get_tile_graph_window()
        self._last_frame_time = 0  # NEU für Ratenberechnung
        self.current_latency = 0   # NEU

        # Heartbeat
        self._last_state = {}
        self.trend_window = config.get_tile_graph_window() 
        # Global Tick
        # Statt 0.5 nehmen wir den Wert aus der Config
        self._main_tick = Clock.schedule_interval(self._global_update, config.get_refresh_interval())
        self.broadcast_active = False
        self.broadcast_data_available = True
        self.broadcast_user_disabled = False

        ######REFACTORING!!!!!
        self.graph_engine = GraphEngine(self)
        self.ui_handler = UIManager(self)
                # CONFIG ENGINE
        self.engine = ConfigEngine(self)
        self.led_engine = LedEngine(self.ui_handler)
        self.mixed_engine = MixedEngine(self)
        self.mixed_engine.init_file()
        self.broadcast_data_available = self.mixed_engine.check_file()
        self.metrics_engine = MetricsEngine(self)
        self.gatt_engine = GattConfigEngine(self)
        self.unit_engine = UnitEngine(self)
        self.swipe_engine = SwipeGestureEngine(self)
        # ActiveChannelEngine initialisieren
        global ACTIVE_CHANNEL_ENGINE
        ACTIVE_CHANNEL_ENGINE = init_active_channel_engine(self.gatt_engine)

        # Android Parity: direkt GATT aktivieren
        self.set_active_channel("gatt")
        
        ##################################
#########REFACTOR

    def get_active_channel(self):
        return ACTIVE_CHANNEL_ENGINE.get_active_channel()

    def set_active_channel(self, channel):
        ACTIVE_CHANNEL_ENGINE.set_active_channel(channel)

    def get_active_index(self):
        return ACTIVE_CHANNEL_ENGINE.get_active_index()

    def set_active_index(self, idx):
        ACTIVE_CHANNEL_ENGINE.set_active_index(idx)

    def next_device(self):
        ACTIVE_CHANNEL_ENGINE.next_device()

    def previous_device(self):
        ACTIVE_CHANNEL_ENGINE.previous_device()

    def get_device_list(self):
        return ACTIVE_CHANNEL_ENGINE.get_device_list()









    def get_broadcast_active(self):
        return self.broadcast_active    
    def set_broadcast_active(self, state: bool):
        self.broadcast_active = state
        self.refresh_all_headers()

    def set_broadcast_available(self, state: bool):
        self.broadcast_data_available = state
    def set_broadcast_user_disabled(self, state: bool):
        self.broadcast_user_disabled = state
        self.refresh_all_headers()



           


     # ---------------------------------------------------------
    # PUBLIC API – Device Switch
    # ---------------------------------------------------------

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
    # Lösche die alten Einzelfunktionen und nimm das:

####
    # ---------------------------------------------------------
    # ZENTRALE GRAPHEN, SMOOTHING & TREND-FABRIK 
    # ---------------------------------------------------------

    def get_graph_data(self, key):
        return self.graph_engine.get_buffer(key)

    def get_trend_icon(self, key):
    # Einfach an die Engine durchreichen
        return self.graph_engine.get_trend_icon(key)
####
####
    # ---------------------------------------------------------
    # UNIT RESOLVER (für Tiles + Fullscreen)
    # ---------------------------------------------------------
    

    # ---------------------------------------------------------
    # UNIT ENGINE – Delegation
    # ---------------------------------------------------------
    
    def get_unit(self, key):
        return self.unit_engine.get_unit(key)
    
    def set_unit(self, key, unit):
        self.unit_engine.set_unit(key, unit)
    
    def toggle_temp_unit(self):
        self.unit_engine.toggle_temp_unit()
    
    def get_temp_unit(self):
        return self.unit_engine.get_temp_unit()

####
    # ---------------------------------------------------------
    # LED Helpers
    # ---------------------------------------------------------
    def _push_led(self):
        # Der GSM sagt nur noch: "Hier ist der Status, verteil das mal!"
        self.ui_handler.update_leds(self.led_state)
    

####



    def bind_screen_manager(self, sm):
        self.screen_manager = sm


    # ---------------------------------------------------------
    # GLOBAL UPDATE TICK!!!
    # ---------------------------------------------------------
    def _global_update(self, dt):
        BUFFER.soft_reload()
        data = BUFFER.get()
    
        if not self.running or not data or not isinstance(data, list):
            self.led_engine.nodata()
            return
    
        # --- MIXED MODE LOGIK ---
        if self.mixed_mode_active:
            self.mixed_engine.update(data)
    
        # Aktives Gerät / Kanal
        idx = min(self.get_active_index(), len(data)-1)
        d = data[idx]
        dev_id = d.get("device_id")
        ch_name = self.get_active_channel()
        ch = d.get(ch_name, {})
        self.metrics_engine.process_metrics(dev_id, ch_name, ch)
        self.metrics_engine.process_vpd_coords(dev_id, ch_name, ch)
        if not isinstance(ch, dict):
            self.led_engine.offline()
            return
    
        # Metriken extrahieren


    

    
        # MAC für UI
        mac = _extract_mac(dev_id)
        d["device_id_flat"] = mac
    
        # Screen Update
        if hasattr(self, 'screen_manager'):
            out = {
                "device_id": d.get("device_id"),
                "device_id_flat": mac,
                "channel": ch_name,
                ch_name: ch,
                "adv": d.get("adv"),
                "gatt": d.get("gatt"),
                "bridge_alive": d.get("bridge_alive"),
                "bridge_status": d.get("bridge_status"),
                "health": d.get("health"),
                "_active_keys": self.extract_active_keys(d)
            }
            self.ui_handler.update_active_screen(self.screen_manager, out)
    
        # Alive / Counter / LED Logik
        alive = ch.get("alive", False)
    
        try:
            current_rssi = d.get("health", {}).get("signal", {}).get("rssi")
            if current_rssi is not None and dev_id:
                self.rssi_history.setdefault(dev_id, []).append(float(current_rssi))
                if len(self.rssi_history[dev_id]) > self.max_history:
                    self.rssi_history[dev_id].pop(0)
        except:
            pass
    
        counter = ch.get("packet_counter")
        raw = ch.get("raw") or ch.get("adv_raw") or ch.get("gat_raw")
    
        if not alive:
            self.led_engine.offline()
            self._last_counter = None
            self._last_raw = None
        else:
            if ch_name == "adv":
                if raw and raw != getattr(self, "_last_raw", None):
                    self.led_engine.flow()
                else:
                    if self.led_engine._flow_hold:
                        self.led_engine.release_flow_hold()
                    else:
                        self.led_engine.stale()
                self._last_raw = raw
            else:  # GATT
                if counter is None or self._last_counter is None:
                    self.led_engine.stale()
                elif counter != self._last_counter:
                    self.led_engine.flow()
                else:
                    if self.led_engine._flow_hold:
                        self.led_engine.release_flow_hold()
                    else:
                        self.led_engine.stale()
                self._last_counter = counter
    
        # Active Keys
        d["_active_keys"] = self.extract_active_keys(d)
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




    def refresh_all_headers(self):
        # Wir holen uns die Liste der Screens jetzt direkt vom neuen Spezialisten!
        for name, ref in self.ui_handler.screens.items():
            # SICHERHEITSGURT: Erst prüfen ob 'ref' existiert, dann ob es 'header' hat
            if ref and hasattr(ref, 'header'):
                if hasattr(ref.header, "btn_broadcast"):
                    ref.header.btn_broadcast._refresh_state()


    # ---------------------------------------------------------
    # PUBLIC: Config Refresh
    # ---------------------------------------------------------
    def refresh_config(self):
        """Einfaches Interface für GSM, alles andere erledigt die Engine"""
        self.engine.refresh()
GLOBAL_STATE = GlobalStateManager()
