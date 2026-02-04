import os
import json
import config
import core

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.graphics import Rectangle, Color
from kivy.utils import platform

from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled

ASSET_ROOT = os.path.join("dashboard_gui", "assets")

def list_bridge_profiles():
    base = os.path.abspath(os.path.join("data", "bridge_profiles"))
    profiles = ["---"]
    if os.path.exists(base):
        profiles += sorted(f[:-5] for f in os.listdir(base) if f.endswith(".json"))
    return profiles

class GrowRoomScreen(Screen):
    name = "grow_rooms"

    def __init__(self, **kw):
        super().__init__(**kw)
        self.device_widgets = {}  # mac -> spinner
        
        # GSM Registrierung
        from dashboard_gui.global_state_manager import GLOBAL_STATE
        GLOBAL_STATE.attach_grow_rooms(self)

        self.root = BoxLayout(orientation="vertical")
        
        # Hintergrund
        with self.root.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(
                source=os.path.join(ASSET_ROOT, "background_grow_room.png"),
                pos=self.pos, size=self.size
            )
        self.bind(pos=self._update_bg, size=self._update_bg)

        # Header
        self.header = HeaderBar()
        self.header.lbl_title.text = "Grow Rooms"
        self.header.update_back_button("grow_rooms")
        self.root.add_widget(self.header)

        # Scroll Body
        self.scroll = ScrollView(do_scroll_x=False)
        self.body = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=dp_scaled(20),
            spacing=dp_scaled(14)
        )
        self.body.bind(minimum_height=self.body.setter("height"))
        self.scroll.add_widget(self.body)
        self.root.add_widget(self.scroll)
        
        self.add_widget(self.root)

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def on_pre_enter(self, *_):
        """Wird aufgerufen, wenn man den Screen betritt - genau wie im SetupScreen"""
        self.refresh_after_config()

    def refresh_after_config(self):
        """Baut die Liste der Geräte jedes Mal neu auf"""
        self.body.clear_widgets()
        self.device_widgets.clear()

        # Info Label
        lbl = Label(
            text="Profile zuweisen & config.json + log_config.json schreiben",
            font_size=sp_scaled(18),
            color=(1, 1, 1, 1),
            size_hint_y=None, height=dp_scaled(40)
        )
        self.body.add_widget(lbl)

        # Config frisch laden
        cfg = config._init()
        devices = cfg.get("devices", {})
        profiles = list_bridge_profiles()

        # Liste der Geräte aufbauen
        for mac, dev in devices.items():
            name = dev.get("name", mac)
            current_profile = dev.get("bridge_profile", "---")

            row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp_scaled(50), spacing=dp_scaled(10))
            row.add_widget(Label(text=f"{name}\n{mac}", size_hint_x=0.6))

            spinner = Spinner(text=current_profile if current_profile else "---", values=profiles, size_hint_x=0.4)
            row.add_widget(spinner)
            
            self.body.add_widget(row)
            self.device_widgets[mac] = spinner

        # Buttons
        btn_save = Button(
            text="SPEICHERN & RELOAD",
            size_hint_y=None,
            height=dp_scaled(56),
            background_color=(0.2, 0.6, 0.2, 1)
        )
        btn_save.bind(on_release=self.save_all)
        self.body.add_widget(btn_save)
        
        btn_restart = Button(
            text="LogBridge RESTART",
            size_hint_y=None,
            height=dp_scaled(56),
            background_color=(0.25, 0.25, 0.25, 1)
        )
        btn_restart.bind(on_release=self.on_logbridge_restart)
        self.body.add_widget(btn_restart)
        
        btn_stop = Button(
            text="LogBridge STOP",
            size_hint_y=None,
            height=dp_scaled(56),
            background_color=(0.6, 0.2, 0.2, 1)
        )
        btn_stop.bind(on_release=self.on_logbridge_stop)
        self.body.add_widget(btn_stop)

    def save_all(self, *_):
        """Speichert in config.json UND log_config.json und macht reload()"""
        # 1. Haupt-Config laden & updaten
        cfg = config._init()
        log_cfg_devices = {}

        for mac, spinner in self.device_widgets.items():
            val = spinner.text if spinner.text != "---" else ""
            if mac in cfg["devices"]:
                cfg["devices"][mac]["bridge_profile"] = val
            
            # Für die log_config.json sammeln
            if val:
                log_cfg_devices[mac] = {"bridge_profile": val}

        # 2. config.json speichern & hart reloaden (wie im Setup)
        config.save(cfg)
        config.reload()

        # 3. log_config.json schreiben
        log_path = os.path.join("data", "log_config.json")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump({"devices": log_cfg_devices}, f, indent=2)

        print("[GrowRoom] Alles gespeichert und reloaded.")
        
        # UI zur Sicherheit nochmal kurz refreshen
        self.refresh_after_config()

    def on_logbridge_restart(self, *_):
        try:
            core.restart_log_bridge()
            print("[GrowRoom] LogBridge restarted")
        except Exception as e:
            print("[GrowRoom] LogBridge RESTART FEHLER:", e)

    def on_logbridge_stop(self, *_):
        try:
            core.stop_log_bridge()
            print("[GrowRoom] LogBridge stopped")
        except Exception as e:
            print("[GrowRoom] LogBridge STOP FEHLER:", e)

    def update_from_global(self, d):
        self.header.update_from_global(d)