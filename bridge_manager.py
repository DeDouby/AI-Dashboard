#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bridge_manager.py – Plattformübergreifende Bridge-Steuerung 🌿
Android: AdvBridge + GattBridge
Desktop: Dummy
© 2025 Dominik Rosenthal (Hackintosh1980)
"""

from kivy.utils import platform
import os
import config


# ------------------------------------------------------------
# 🧩 Bridge-Basisinterface
# ------------------------------------------------------------
class BridgeInterface:
    def start(self): ...
    def stop(self): ...
    def get_status(self):
        return {
            "running": False,
            "bt_enabled": False,
            "source": "unknown"
        }


# ------------------------------------------------------------
# 🤖 Android-Implementierung (ADV + GATT getrennt)
# ------------------------------------------------------------
class BleBridgeAndroid(BridgeInterface):
    def __init__(self):
        self.running_adv = False
        self.running_gatt = False
        self.running_log = False
        self.bt_enabled = False

    # -------------------------
    # ADV
    # -------------------------
    def start_adv(self):
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        ctx = PythonActivity.mActivity
        AdvBridge = autoclass("org.hackintosh1980.blebridge.AdvBridge")

        ret = AdvBridge.start(ctx)
        print("[BridgeAndroid] ADV start →", ret)
        self.running_adv = True
        self.bt_enabled = True

    def stop_adv(self):
        from jnius import autoclass
        autoclass("org.hackintosh1980.blebridge.AdvBridge").stop()
        self.running_adv = False

    # -------------------------
    # GATT
    # -------------------------
    def start_gatt(self):
        from jnius import autoclass
        import os, config

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        ctx = PythonActivity.mActivity
        GattBridge = autoclass("org.hackintosh1980.blebridge.GattBridge")

        gatt_cfg = os.path.join(config.DATA, "gatt_config.json")
        ret = GattBridge.start(ctx, gatt_cfg)

        print("[BridgeAndroid] GATT start →", gatt_cfg)
        self.running_gatt = True
        self.bt_enabled = True

    def stop_gatt(self):
        from jnius import autoclass
        autoclass("org.hackintosh1980.blebridge.GattBridge").stop()
        self.running_gatt = False

# LogBridge 

    # -------------------------
    # LOG
    # -------------------------
    def start_log(self):
        from jnius import autoclass
        import os, config
    
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        ctx = PythonActivity.mActivity
        LogBridge = autoclass("org.hackintosh1980.blebridge.LogBridge")
    
        out_name = "ble_log_dump.json"
        ret = LogBridge.start(ctx, out_name)
    
        print("[BridgeAndroid] LOG start →", out_name)
        self.running_log = True
        self.bt_enabled = True
    
    
    def stop_log(self):
        from jnius import autoclass
        autoclass("org.hackintosh1980.blebridge.LogBridge").stop()
        self.running_log = False
    # -------------------------
    # Backward compatibility
    # -------------------------
    def start(self):
        self.start_adv()
        self.start_gatt()

    def stop(self):
        self.stop_adv()
        self.stop_gatt()

# ------------------------------------------------------------
# 🖥️ Plattformwahl
# ------------------------------------------------------------
def get_bridge(prefer_mock=False) -> BridgeInterface:
    if platform == "android":
        return BleBridgeAndroid()
    return BridgeInterface()
