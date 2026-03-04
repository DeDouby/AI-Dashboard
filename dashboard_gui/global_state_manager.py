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
from dashboard_gui.engines.multi_active_key_engine import MultiActiveKeyEngine
from dashboard_gui.engines.tile_engine import TileEngine
# In deiner global_state_manager.py
from dashboard_gui.global_gesture_manager import GlobalGestureManager
from dashboard_gui.engines.data_flow_engine import DataFlowEngine
from dashboard_gui.engines.broadcast_engine import BroadcastEngine

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

        self.max_history = config.get_tile_graph_window()

        # Heartbeat
        self.trend_window = config.get_tile_graph_window() 
        # Global Tick
        # Statt 0.5 nehmen wir den Wert aus der Config
        self._main_tick = Clock.schedule_interval(self._global_update, config.get_refresh_interval())


        ######REFACTORING!!!!!
        self.graph_engine = GraphEngine(self)
        self.ui_handler = UIManager(self)
                # CONFIG ENGINE
        self.engine = ConfigEngine(self)
        self.led_engine = LedEngine(self.ui_handler)
        self.mixed_engine = MixedEngine(self)
        self.mixed_engine.init_file()
        self.metrics_engine = MetricsEngine(self)
        self.gatt_engine = GattConfigEngine(self)
        self.unit_engine = UnitEngine(self)
        self.multi_key_engine = MultiActiveKeyEngine(self)
        self.tile_engine = TileEngine(self)
        self.ggm = GlobalGestureManager(self)
        self.broadcast_engine = BroadcastEngine(self)
        self.data_flow = DataFlowEngine(self)
        from dashboard_gui.engines.active_channel_engine import init_active_channel_engine
        
        # 2. ERSCHAFFE die Engine und binde sie an self (WICHTIG!)
        self.active_channel_engine = init_active_channel_engine(self.gatt_engine)
        
        # 3. Jetzt, wo sie existiert, kannst du sie der globalen Variable zuweisen
        global ACTIVE_CHANNEL_ENGINE
        ACTIVE_CHANNEL_ENGINE = self.active_channel_engine
        ##################################
#########REFACTOR
    def sync_ui_buttons(self):
        """Triggert den Sync-Vorgang im UI Manager an."""
        self.ui_handler._refresh_all_buttons()
# Füge diese Methode im GlobalStateManager hinzu:
    def get_active_device_id(self):
        """Gibt die ID des aktuell angewählten Geräts zurück."""
        try:
            # Jetzt existiert self.active_channel_engine!
            idx = self.active_channel_engine.get_active_index()
            dev_list = self.active_channel_engine.get_device_list()
            
            if dev_list and idx < len(dev_list):
                return dev_list[idx]
        except Exception as e:
            print(f"[GSM] Error getting active device id: {e}")
        return None

    def get_active_channel(self):
        # Wir delegieren die Anfrage an die tatsächliche Engine
        from dashboard_gui.engines.active_channel_engine import ACTIVE_CHANNEL
        return ACTIVE_CHANNEL.get_active_channel()
    # In global_state_manager.py
    def set_active_channel(self, channel):
        self.active_channel_engine.set_active_channel(channel)
        # Kleiner Trick: Wir triggern hier direkt den Flow, dann muss das Menü es nicht tun!
        self.data_flow.process_cycle()

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

# --- BROADCAST DELEGATION ---
    def get_broadcast_active(self):
        return self.broadcast_engine.active    

    def set_broadcast_active(self, state):
        # Ruft die neue Engine-Logik auf (inkl. core start/stop)
        self.broadcast_engine.set_active(state)

    def set_broadcast_available(self, state: bool):
        self.broadcast_engine.set_available(state)

    def set_broadcast_user_disabled(self, state: bool):
        self.broadcast_engine.set_user_disabled(state)

    def refresh_all_headers(self):
        # Delegiert an den UI-Manager
        self.ui_handler.refresh_broadcast_buttons()

    # ---------------------------------------------------------
    # TILE ENGINE – Delegation
    # ---------------------------------------------------------

    def register_tiles(self, tiles):
        self.tile_engine.register_tiles(tiles)

    def get_active_tiles(self):
        return self.tile_engine.get_active_tiles()

    def build_tile_key(self, device_id, channel, tile_id):
        return self.tile_engine.build_full_key(device_id, channel, tile_id)

    def next_tile(self, tile_id, direction):
        return self.tile_engine.get_next_tile(tile_id, direction)

    def next_tile_key(self, full_key, direction):
        return self.tile_engine.get_next_full_key(full_key, direction)


           


     # ---------------------------------------------------------
    # PUBLIC API – Device Switch
    # ---------------------------------------------------------
    def get_device_label(self, device_id):
        try:
            cfg = config._init()
            devices = cfg.get("devices", {})
            dev = devices.get(device_id, {})
            return dev.get("name") or device_id
        except:
            return device_id
####

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
    # Der neue, saubere Tick:
    def _global_update(self, dt):
        # Alles delegiert an die Spezial-Engine
        self.data_flow.process_cycle()
 ####
    # ---------------------------------------------------------
    # Active Keys – MULTI-CHANNEL (adv + gatt, ohne Vorrang) MIXED MODE
    # ---------------------------------------------------------
    def extract_active_keys(self, d):
        return self.multi_key_engine.extract_active_keys(d)

    def refresh_all_headers(self):
        # Nutzt jetzt den ui_handler
        self.ui_handler.refresh_broadcast_buttons()


    # ---------------------------------------------------------
    # PUBLIC: Config Refresh
    # ---------------------------------------------------------
    def refresh_config(self):
        """Einfaches Interface für GSM, alles andere erledigt die Engine"""
        self.engine.refresh()
GLOBAL_STATE = GlobalStateManager()
