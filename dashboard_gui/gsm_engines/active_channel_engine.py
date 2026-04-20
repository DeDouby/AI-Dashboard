# dashboard_gui/engines/active_channel_engine.py
import config
import core

class ActiveChannelEngine:
    def __init__(self, gatt_config_engine):
        self.active_index = 0
        self.active_channel = "webserver"
        self._last_counter = None
        self.gatt_config_engine = gatt_config_engine

    # ---------------------------------------------------------
    # Channel Management
    # ---------------------------------------------------------
    def set_active_channel(self, channel):
        # ERWEITERT: "webserver" zur Erlaubnisliste hinzufügen
        if channel not in ("adv", "gatt", "webserver"):
            return
        if channel == self.active_channel:
            return

        prev = self.active_channel
        self.active_channel = channel
        self._last_counter = None

        print(f"[ACE] Channel -> {channel}")

        try:
            # 1. Aktuelle Geräte-ID ermitteln
            item = self.get_device_list()[self.active_index]
            device_id = item.get("device_id") if isinstance(item, dict) else item

            # 2. Kanal-spezifische Hardware-Aktionen (Bridge starten/stoppen)
            cfg = config._init()
            dev = cfg.get("devices", {}).get(device_id, {})
            bridge_profile = dev.get("bridge_profile", "")

            if prev == "adv" and channel == "gatt":
                if bridge_profile:
                    self.gatt_config_engine.write(device_id)
            elif prev == "gatt" and channel == "adv":
                try:
                    core.stop_gatt_bridge()
                    print("[ACE] GATT Bridge stopped")
                except Exception as e:
                    print("[ACE] stop_gatt_bridge failed:", e)

            # ---------------------------------------------------------
            # NEU: IDIOTENSICHERER FULLSCREEN-RESET
            # ---------------------------------------------------------
            # Wenn wir den Kanal wechseln, ändern sich oft die verfügbaren Daten.
            # Wir zwingen den Fullscreen, auf das erste Tile des neuen Kanals zu springen.
            
            if hasattr(self.gatt_config_engine, "gsm"):
                    gsm = self.gatt_config_engine.gsm
                    
                    # 1. Wahrheit abgreifen
                    allowed = gsm.tile_engine.get_active_tiles()
                    if allowed:
                        # 2. Key für das erste Tile bauen
                        new_key = f"{device_id}_{channel}_{allowed[0]}"
                        
                        # 3. Fullscreen zwingen
                        fs_screen = gsm.ui_handler.get_screen("fullscreen")
                        if fs_screen:
                            fs_screen.activate_tile(new_key)

        except Exception as e:
            print("[ACE] channel switch failed:", e)

    def get_active_channel(self):
        return self.active_channel

    # ---------------------------------------------------------
    # Device Management
    # ---------------------------------------------------------
    def next_device(self):
        lst = self.get_device_list()
        if not lst:
            return
        self.set_active_index((self.active_index + 1) % len(lst))

    def previous_device(self):
        lst = self.get_device_list()
        if not lst:
            return
        self.set_active_index((self.active_index - 1) % len(lst))

    def set_active_index(self, idx):
        idx = max(0, int(idx))
        if idx == self.active_index:
            return

        self.active_index = idx
        self._last_counter = None
        print(f"[ACE] Active device -> {idx}")

        try:
            item = self.get_device_list()[self.active_index]
            device_id = item.get("device_id") if isinstance(item, dict) else item

            if self.active_channel == "gatt":
                cfg = config._init()
                dev = cfg.get("devices", {}).get(device_id, {})
                bridge_profile = dev.get("bridge_profile", "")
                if bridge_profile:
                    self.gatt_config_engine.write(device_id)
                    
        except Exception as e:
            print("[ACE] device switch failed:", e)

    def get_active_index(self):
        return self.active_index

    def get_device_list(self):
        cfg = config._init()
        devs = cfg.get("devices", {})
        if not isinstance(devs, dict):
            return []
        return list(devs.keys())

    def get_device_label(self, device_id):
        cfg = config._init()
        d = cfg.get("devices", {}).get(device_id, {})
        return d.get("name", device_id)

    # KEINE global ACTIVE_CHANNEL mehr exportieren!
    def get_active_channel_engine():
        return ACTIVE_CHANNEL  # nur intern
# Singleton
ACTIVE_CHANNEL = None

def init_active_channel_engine(gatt_config_engine):
    global ACTIVE_CHANNEL
    ACTIVE_CHANNEL = ActiveChannelEngine(gatt_config_engine)
    return ACTIVE_CHANNEL