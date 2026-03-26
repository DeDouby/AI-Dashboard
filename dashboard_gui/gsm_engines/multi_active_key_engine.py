# dashboard_gui/engines/multi_active_key_engine.py
from typing import List, Dict, Set

class MultiActiveKeyEngine:
    """
    Verantwortlich für die Berechnung der aktiven Keys pro Gerät,
    Multi-Channel (adv + gatt) und Mixed-Mode.
    """

    def __init__(self, gsm):
        self.gsm = gsm

    # ---------------------------------------------------------
    # Multi-Channel Active Keys
    # ---------------------------------------------------------
    def extract_active_keys(self, frame: Dict) -> List[str]:
        """
        Ermittelt alle aktiven Keys für adv + gatt Kanäle, interne + externe Werte
        """
        active: Set[str] = set()

        for ch_name in ("adv", "gatt", "webserver"):
            ch = frame.get(ch_name)
            if not isinstance(ch, dict):
                continue
            # interne/externe Werte prüfen wie bisher

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

    # ---------------------------------------------------------
    # Mixed Mode Device Selection Helpers
    # ---------------------------------------------------------
    def toggle_device_selection(self, dev_id: str):
        """Device in Mixed Mode selektieren / deselect"""
        selected = self.gsm.mixed_selected_buffers
        if dev_id in selected:
            selected.remove(dev_id)
            self.gsm.mixed_device_modes.pop(dev_id, None)
        else:
            selected.add(dev_id)
            self.gsm.mixed_device_modes[dev_id] = {"internal"}

    def toggle_device_mode(self, dev_id: str, mode: str):
        """Internal / External Mode Toggle pro Device"""
        modes = self.gsm.mixed_device_modes.get(dev_id, {"internal"})
        if mode in modes and len(modes) > 1:
            modes.remove(mode)
        else:
            modes.add(mode)
        self.gsm.mixed_device_modes[dev_id] = modes