# setup_screen.py – Session42 FIXED CLEAN (REPAIRED)

import os
import json
import time

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.utils import platform
from kivy.metrics import dp

from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled

from dashboard_gui.ui.setup_content.setup_main_panel import SetupMainPanel
from dashboard_gui.ui.common.header_online import HeaderBar
import config
from dashboard_gui.global_state_manager import GLOBAL_STATE
import core
import config

_selected = {}      # mac -> { "adv": str, "gatt": str, "bridge": str }
_device_names = {}  # mac -> display name   ✅ FEHLTE


def _raw_path():
    return os.path.join(config.DATA, "ble_dump.json")



class SetupScreen(Screen):

    def __init__(self, **kw):
        super().__init__(**kw)
        self._devices_loaded_once = False

        from dashboard_gui.global_state_manager import GLOBAL_STATE
        GLOBAL_STATE.ui_handler.attach_screen("setup", self)

        # 1) ROOT OHNE PADDING (Damit der Header oben klebt)
        root = BoxLayout(orientation="vertical", spacing=0, padding=0)
        self.add_widget(root)

        # 2) Header (Jetzt perfekt im Gleichtakt)
        self.header = HeaderBar()
        self.header.lbl_title.text = "Setup"
        self.header.update_back_button("setup")
        root.add_widget(self.header)

        # 3) CONTENT-CONTAINER MIT PADDING (Nur für das Panel)
        # Hier packen wir die 10px spacing/padding rein, die du für die Optik willst
        content_box = BoxLayout(orientation="vertical", spacing=10, padding=10)        


        self.panel = SetupMainPanel(
            on_refresh=self.update_devices,
            on_save=self._save,
            on_back=self._back,
            on_profile_change=self._set_profile,
            on_device_toggle=self._toggle_device,  # <-- hier Callback
            on_adv=self.set_adv,
            on_gatt=self.set_gatt,
            on_bridge=self.set_bridge,
            on_restart_bridge=self._restart_bridge,
            on_restart_adv=self._restart_adv,
            on_restart_gatt=self._restart_gatt,
        )
        content_box.add_widget(self.panel)
        root.add_widget(content_box) # Die Box kommt UNTER den Header

    def on_pre_enter(self, *_):
        if not self._devices_loaded_once:
            self._devices_loaded_once = True
            Clock.schedule_once(self.update_devices, 0)

    def _restart_adv(self, *_):
        try:
            import core
            core.restart_adv_bridge()
            print("[Setup] ADV Bridge neu gestartet")
        except Exception as e:
            print("[Setup] ADV restart FEHLER:", e)
    
    def _restart_gatt(self, *_):
        try:
            import core
            core.restart_gatt_bridge()
            print("[Setup] GATT Bridge neu gestartet")
        except Exception as e:
            print("[Setup] GATT restart FEHLER:", e)


    # ---------------------------------------------------------
    # ---------------------------------------------------------
    # SetupScreen – Bridge-only Restart (ohne Core, ohne Dump)
    # ---------------------------------------------------------
    def _restart_bridge(self, *_):
        try:
            from bridge_manager import get_bridge
    
            bridge = get_bridge()
            bridge.stop()
            bridge.start()
    
            print("[Setup] ADV + GATT Bridges neu gestartet (Bridge-only)")
    
        except Exception as e:
            print("[Setup] Bridge-only Restart FEHLER:", e)

    # ---------------------------------------------------------
    # ---------------------------------------------------------
    def update_devices(self, *_):
        self.panel.clear_devices()
    
        path = _raw_path()
        if not os.path.exists(path):
            print("[Setup] dump fehlt")
            return
    
        try:
            with open(path, "r", encoding="utf-8") as f:
                arr = json.load(f)
        except Exception:
            print("[Setup] JSON Fehler")
            return
    
        for e in arr:
            mac = e.get("address")
            raw = e.get("adv_raw") or e.get("gat_raw") or e.get("log_raw")
            name = e.get("name") or mac
    
            if not mac or not raw:
                continue
    
            _device_names[mac] = name
    
            if not config.is_developer_mode():
                lname = name.lower()
                if not (
                    "sps" in lname
                    or "thermobeacon" in lname
                    or "tp35" in lname
                    or "thermopro" in lname
                ):
                    continue
    
                # immer Dict verwenden, nicht True
                sel = _selected.get(mac, {
                    "adv": config.get_adv_decoder(mac),
                    "gatt": config.get_gatt_decoder(mac),
                    "bridge": config.get_bridge_profile(mac)
                })
    
                _selected[mac] = sel  # sicherstellen
    
                self.panel.add_device(
                    name=name,
                    mac=mac,
                    selected=True
                )
    # 🔑 Dev-Mode Default: einmal sauber vorbelegen
            else:
                if mac not in _selected:
                    lname = name.lower()
            
                    if "sps" in lname:
                        _selected[mac] = {
                            "adv": "Inkbird_ADV_Desktop",
                            "gatt": "Inkbird_GATT",
                            "bridge": "Inkbird_Bridge"
                        }
                    elif "thermobeacon" in lname:
                        _selected[mac] = {
                            "adv": "ThermoBeacon2_ADV",
                            "gatt": "ThermoBeacon2_GATT",
                            "bridge": "ThermoBeacon2_Bridge"
                        }
                    elif "tp35" in lname or "thermopro" in lname:
                        _selected[mac] = {
                            "gatt": "ThermoPro_GATT",
                            "bridge": "ThermoPro_Bridge"
                        }
                    else:
                        _selected[mac] = {
                            "adv": "",
                            "gatt": "",
                            "bridge": ""
                        }
            
                sel = _selected[mac]
            
                self.panel.add_device(
                    name=name,
                    adv=sel.get("adv"),
                    gatt=sel.get("gatt"),
                    bridge=sel.get("bridge"),
                    mac=mac
                )
    # ---------------------------------------------------------
    def _set_profile(self, mac, prof):
        _selected[mac] = {"profile": prof}

    # ---------------------------------------------------------
    # 🔥 SetupScreen _save() – GATT automatisch wie Header
    # ---------------------------------------------------------
    def _save(self, *_):
        import core
        from dashboard_gui.global_state_manager import GLOBAL_STATE
        from kivy.app import App
    
        # -------------------------
        # 1) Config zusammenstellen
        # -------------------------
        cfg = config._init()
        devices = {}
    
        for mac, sel in _selected.items():
            name = _device_names.get(mac, mac)
    
            if not config.is_developer_mode():
                lname = name.lower()
            
                if "sps" in lname:
                    sel = {
                        "adv": "Inkbird_ADV_Desktop",
                        "gatt": "Inkbird_GATT",
                        "bridge": "Inkbird_Bridge"
                    }
            
                elif "thermobeacon" in lname:
                    sel = {
                        "adv": "ThermoBeacon2_ADV",
                        "gatt": "ThermoBeacon2_GATT",
                        "bridge": "ThermoBeacon2_Bridge"
                    }
            
                elif "tp35" in lname or "thermopro" in lname:
                    sel = {
                        "gatt": "ThermoPro_GATT",
                        "bridge": "ThermoPro_Bridge"
                    }
            
                else:
                    continue
            
                _selected[mac] = sel
    
            adv = sel.get("adv", "")
            gatt = sel.get("gatt", "")
            bridge = sel.get("bridge", "")
    
            # nur speichern, wenn mindestens eines gesetzt ist
            if any([adv, gatt, bridge]):
                devices[mac] = {
                    "name": name,
                    "adv_decoder": adv,
                    "gatt_decoder": gatt,
                    "bridge_profile": bridge
                }
    
        # 🔒 Absicherung: niemals leere devices speichern
        if not devices:
            print("[Setup] Kein Device zum Speichern – Config bleibt unverändert")
            return
    
        cfg["devices"] = devices
        config.save(cfg)
        config.reload()

        print("[Setup] Config gespeichert")
    
        # -------------------------
        # 2) GATT Bridge gezielt für Device 0 schreiben + Restart
        # -------------------------
        try:
            device_list = list(devices.keys())
            if not device_list:
                raise RuntimeError("keine Devices nach Setup")
        
            # 🔒 IMMER Device 0
            device_id = device_list[0]
            dev = devices.get(device_id, {})
            bridge_profile = dev.get("bridge_profile", "")
        
            if bridge_profile:
                GLOBAL_STATE.write_gatt_bridge_config(device_id)
                print(f"[Setup] GATT config geschrieben für Device 0: {device_id}")
            else:
                print("[Setup] Device 0 hat kein bridge_profile")
        
            # GSM sauber initialisieren
            GLOBAL_STATE.set_active_index(0)
            GLOBAL_STATE.set_active_channel("gatt")
        
            # Bridge EINMAL neu starten
            core.restart_gatt_bridge()
        
        except Exception as e:
            print("[Setup] Fehler bei GATT Auto-Activate:", e)    
        # -------------------------
        # 3) Direkt ins Dashboard springen
        # -------------------------
        if self.manager:
            self.manager.current = "dashboard"

    # ---------------------------------------------------------
    def _back(self, *_):
        if self.manager:
            self.manager.current = "dashboard"

    def set_adv(self, mac, val):
        if val == "---":
            _selected.setdefault(mac, {}).pop("adv", None)
        else:
            _selected.setdefault(mac, {})["adv"] = val

    def set_gatt(self, mac, val):
        if val == "---":
            _selected.setdefault(mac, {}).pop("gatt", None)
        else:
            _selected.setdefault(mac, {})["gatt"] = val

    def set_bridge(self, mac, val):
        if val == "---":
            _selected.setdefault(mac, {}).pop("bridge", None)
        else:
            _selected.setdefault(mac, {})["bridge"] = val

    # neue Funktion für Toggle
    def _toggle_device(self, mac, is_selected):
        if is_selected:
            _selected.setdefault(mac, {})["adv"] = config.get_adv_decoder(mac)
            _selected[mac]["gatt"] = config.get_gatt_decoder(mac)
            _selected[mac]["bridge"] = config.get_bridge_profile(mac)
        else:
            _selected.pop(mac, None)
    # ---------------------------------------------------------
    # LIVE UPDATE FROM GSM (nur Header)
    # ---------------------------------------------------------
    def update_from_global(self, d):
        self.header.update_from_global(d)
        self.header._last_frame = d
