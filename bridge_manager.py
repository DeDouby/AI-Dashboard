#bridgemanager
from kivy.utils import platform
import os
import config

# Absolute Singleton-Instanz
_bridge_instance = None

class BleBridgeAndroid:
    def __init__(self):
        from jnius import autoclass
        self.PythonActivity = autoclass("org.kivy.android.PythonActivity")
        self.AdvBridge = autoclass("org.hackintosh1980.blebridge.AdvBridge")
        self.GattBridge = autoclass("org.hackintosh1980.blebridge.GattBridge")
        self.BroadcastBridge = autoclass("org.hackintosh1980.blebridge.BroadcastBridge")
        self.LogBridge = autoclass("org.hackintosh1980.blebridge.LogBridge")
        self.ctx = self.PythonActivity.mActivity

    def start(self):
        self.start_adv()
        
    def start_adv(self):
        self.AdvBridge.start(self.ctx)

    def stop_adv(self):
        self.AdvBridge.stop()
    def start_gatt(self):
        gatt_cfg = os.path.join(config.DATA, "gatt_config.json")
        self.GattBridge.start(self.ctx, gatt_cfg)

    def stop_gatt(self):
        self.GattBridge.stop()

    def start_broadcast(self):
        mixed_path = os.path.join(config.DATA, "mixed.json")
        self.BroadcastBridge.start(self.ctx, mixed_path)

    def stop_broadcast(self):
        self.BroadcastBridge.stop()

    def start_log(self):
        self.LogBridge.start(self.ctx, "ble_log_dump.json")

    def stop_log(self):
        self.LogBridge.stop()

    def stop(self):
        self.stop_adv()
        self.stop_gatt()
        self.stop_broadcast()

def get_bridge(prefer_mock=False):
    global _bridge_instance
    if _bridge_instance is None:
        if platform == "android":
            _bridge_instance = BleBridgeAndroid()
        else:
            # Dummy Klasse für Desktop
            class Dummy:
                def __getattr__(self, name): return lambda *a, **k: None
            _bridge_instance = Dummy()
    return _bridge_instance