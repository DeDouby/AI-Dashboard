###############################################################################
# GROW CONTROLLER - Zentrale Systemeinstellungen
###############################################################################

import os
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.graphics import Rectangle, Color
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.widget import Widget

from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.global_state_manager import GLOBAL_STATE

ASSET_ROOT = os.path.join("dashboard_gui", "assets")


class GrowControllerScreen(Screen):
    name = "grow_controller"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        GLOBAL_STATE.ui_handler.attach_screen("grow_controller", self)

        self.root = BoxLayout(orientation="vertical")

        # Hintergrund
        with self.root.canvas.before:
            Color(0.05, 0.05, 0.07, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)
        # Hintergrund
        with self.root.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(
                source=os.path.join(ASSET_ROOT, "background_grow_controller.png"),
                pos=self.pos, size=self.size
            )
        self.bind(pos=self._update_bg, size=self._update_bg)
        # Header
        self.header = HeaderBar()
        self.header.lbl_title.text = "GROW CONTROLLER"
        self.header.update_back_button("grow_controller")
        self.root.add_widget(self.header)

        # Scrollable Body
        self.scroll = ScrollView(do_scroll_x=False)
        self.body = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=dp_scaled(20),
            spacing=dp_scaled(16)
        )
        self.body.bind(minimum_height=self.body.setter('height'))
        self.scroll.add_widget(self.body)
        self.root.add_widget(self.scroll)

        self.add_widget(self.root)

        Clock.schedule_once(self.build_ui, 0.2)

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def build_ui(self, *_):
        self.body.clear_widgets()

        # ==================== SYSTEM INFO ====================
        self.body.add_widget(self._create_section_title("SYSTEM INFORMATION"))

        self.body.add_widget(self._create_info_row("ESP Firmware", "v2.4.1-beta"))
        self.body.add_widget(self._create_info_row("Uptime", "14d 7h 23m"))
        self.body.add_widget(self._create_info_row("WiFi Signal", "-68 dBm (sehr gut)"))
        self.body.add_widget(self._create_info_row("IP-Adresse", "192.168.2.39"))
        self.body.add_widget(self._create_info_row("MAC", "A4:CF:12:78:9A:BC"))

        # ==================== TIME & SYNC ====================
        self.body.add_widget(self._create_section_title("TIME & SYNCHRONISATION"))

        self.body.add_widget(self._create_info_row("Aktuelle ESP Zeit", "12.04.2026  03:14"))
        self.body.add_widget(self._create_button_row("Uhrzeit mit Handy abgleichen", self.sync_time))

        # ==================== NETWORK & GATEWAY ====================
        self.body.add_widget(self._create_section_title("NETWORK & GATEWAY"))

        self.body.add_widget(self._create_info_row("Gateway / MQTT Broker", "192.168.2.10:1883"))
        self.body.add_widget(self._create_button_row("Gateway neu verbinden", self.reconnect_gateway))

        # ==================== SENSORS & DEVICES ====================
        self.body.add_widget(self._create_section_title("SENSORS & DEVICES"))

        self.body.add_widget(self._create_button_row("Verfügbare Sensoren verwalten", self.manage_sensors))
        self.body.add_widget(self._create_button_row("BLE Geräte verwalten", self.manage_ble))

        # ==================== ADVANCED ====================
        self.body.add_widget(self._create_section_title("ADVANCED SETTINGS"))

        self.body.add_widget(self._create_button_row("Log Level ändern", self.change_log_level))
        self.body.add_widget(self._create_button_row("Factory Reset (ESP)", self.factory_reset))
        self.body.add_widget(self._create_button_row("Firmware Update", self.firmware_update))

        # Spacer
        self.body.add_widget(Widget(size_hint_y=None, height=dp_scaled(30)))

    def _create_section_title(self, text):
        lbl = Label(
            text=text,
            font_size=sp_scaled(17),
            bold=True,
            color=(0, 1, 0, 0.9),
            size_hint_y=None,
            height=dp_scaled(38),
            halign="left"
        )
        lbl.bind(size=lambda *x: setattr(lbl, 'text_size', (lbl.width, None)))
        return lbl

    def _create_info_row(self, label, value):
        row = BoxLayout(size_hint_y=None, height=dp_scaled(42), spacing=dp_scaled(10))
        row.add_widget(Label(text=label, halign="left", size_hint_x=0.55, color=(0.85, 0.85, 0.85, 1)))
        row.add_widget(Label(text=value, halign="right", size_hint_x=0.45, color=(1, 1, 1, 0.85)))
        return row

    def _create_button_row(self, text, callback):
        btn = Button(
            text=text,
            size_hint_y=None,
            height=dp_scaled(52),
            background_color=(0.15, 0.15, 0.18, 1),
            color=(1, 1, 1, 1),
            font_size=sp_scaled(15.5),
            bold=False
        )
        btn.bind(on_release=callback)
        return btn

    # ==================== Button Actions (Dummy) ====================
    def sync_time(self, *_):
        print("[GrowController] → Zeit mit Handy synchronisiert")

    def reconnect_gateway(self, *_):
        print("[GrowController] → Gateway neu verbunden")

    def manage_sensors(self, *_):
        print("[GrowController] → Sensor Management geöffnet")

    def manage_ble(self, *_):
        print("[GrowController] → BLE Device Manager geöffnet")

    def change_log_level(self, *_):
        print("[GrowController] → Log Level geändert")

    def factory_reset(self, *_):
        print("[GrowController] → Factory Reset angefordert")

    def firmware_update(self, *_):
        print("[GrowController] → Firmware Update gestartet")

    def update_from_global(self, data):
        self.header.update_from_global(data)