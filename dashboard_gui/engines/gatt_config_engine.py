import json
import os
import config


class GattConfigEngine:

    def __init__(self, gsm):
        self.gsm = gsm

    # ---------------------------------------------------------
    # WRITE GATT BRIDGE CONFIG
    # ---------------------------------------------------------
    def write(self, device_id):

        cfg = config._init()
        dev = cfg.get("devices", {}).get(device_id)

        if not dev:
            print(f"[GATT_CFG] Kein Device in config: {device_id}")
            return

        bridge_profile = dev.get("bridge_profile", "")
        if not bridge_profile:
            print(f"[GATT_CFG] Kein bridge_profile für {device_id}")
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

        print(f"[GATT_CFG] gatt_config.json geschrieben für {device_id}")