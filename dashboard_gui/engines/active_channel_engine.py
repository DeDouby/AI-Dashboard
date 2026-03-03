# dashboard_gui/engines/active_channel_engine.py
import config
import core

class ActiveChannelEngine:
    def __init__(self, gatt_config_engine):
        self.active_index = 0
        self.active_channel = "adv"
        self._last_counter = None
        self.gatt_config_engine = gatt_config_engine

    # ---------------------------------------------------------
    # Channel Management
    # ---------------------------------------------------------
    def set_active_channel(self, channel):
        if channel not in ("adv", "gatt"):
            return
        if channel == self.active_channel:
            return

        prev = self.active_channel
        self.active_channel = channel
        self._last_counter = None

        print(f"[ACE] Channel -> {channel}")

        try:
            item = self.get_device_list()[self.active_index]
            device_id = item.get("device_id") if isinstance(item, dict) else item

            cfg = config._init()
            dev = cfg.get("devices", {}).get(device_id, {})
            bridge_profile = dev.get("bridge_profile", "")

            # ADV → GATT
            if prev == "adv" and channel == "gatt":
                if bridge_profile:
                    self.gatt_config_engine.write(device_id)
                    core.restart_gatt_bridge()
            # GATT → ADV
            elif prev == "gatt" and channel == "adv":
                pass  # ADV Restart nicht nötig
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
                    core.restart_gatt_bridge()
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


# Singleton
ACTIVE_CHANNEL = None

def init_active_channel_engine(gatt_config_engine):
    global ACTIVE_CHANNEL
    ACTIVE_CHANNEL = ActiveChannelEngine(gatt_config_engine)
    return ACTIVE_CHANNEL