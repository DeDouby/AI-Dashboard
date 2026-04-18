import os
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
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
        
        with self.root.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_image = Rectangle(
                source=os.path.join(ASSET_ROOT, "background_grow_controller.png"),
                pos=self.pos, size=self.size
            )
        self.bind(pos=self._update_bg, size=self._update_bg)

        # Header
        self.header = HeaderBar()
        self.header.lbl_title.text = "GROW CONTROLLER"
        self.header.update_back_button("grow_controller")
        self.root.add_widget(self.header)

        # Scrollable Body mit GridLayout (2 Spalten)
        self.scroll = ScrollView(do_scroll_x=False)
        self.body = GridLayout(
            cols=2,
            size_hint_y=None,
            padding=dp_scaled(20),
            spacing=dp_scaled(12)
        )
        self.body.bind(minimum_height=self.body.setter('height'))
        self.scroll.add_widget(self.body)
        self.root.add_widget(self.scroll)

        self.add_widget(self.root)

        Clock.schedule_once(self.build_ui, 0.2)

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.bg_image.pos = self.pos
        self.bg_image.size = self.size

    def build_ui(self, *_):
        self.body.clear_widgets()

        # ==================== SYSTEM INFO ====================
        self._add_wide_widget(self._create_section_title("SYSTEM INFORMATION"))
        self.body.add_widget(self._create_info_card("ESP Firmware", "v2.4.1-beta"))
        self.body.add_widget(self._create_info_card("Uptime", "14d 7h 23m"))
        self.body.add_widget(self._create_info_card("WiFi Signal", "-68 dBm"))
        self.body.add_widget(self._create_info_card("IP-Adresse", "192.168.2.39"))
        self.body.add_widget(self._create_info_card("MAC", "A4:CF:12:78:9A:BC"))
        self.body.add_widget(Widget(size_hint_y=None, height=1)) # Filler für ungerade Anzahl

        # ==================== TIME & SYNC ====================
        self._add_wide_widget(self._create_section_title("TIME & SYNCHRONISATION"))
        self.body.add_widget(self._create_info_card("Aktuelle Zeit", "12.04.26 03:14"))
        self.body.add_widget(self._create_button_row("Zeit synchronisieren", self.sync_time))

        # ==================== NETWORK & GATEWAY ====================
        self._add_wide_widget(self._create_section_title("NETWORK & GATEWAY"))
        self.body.add_widget(self._create_info_card("MQTT Broker", "192.168.2.10"))
        self.body.add_widget(self._create_button_row("Gateway Connect", self.reconnect_gateway))

        # ==================== SENSORS & DEVICES ====================
        self._add_wide_widget(self._create_section_title("SENSORS & DEVICES"))
        self.body.add_widget(self._create_button_row("Sensoren verwalten", self.manage_sensors))
        self.body.add_widget(self._create_button_row("BLE verwalten", self.manage_ble))

        # ==================== ADVANCED ====================
        self._add_wide_widget(self._create_section_title("ADVANCED SETTINGS"))
        self.body.add_widget(self._create_button_row("Log Level", self.change_log_level))
        self.body.add_widget(self._create_button_row("Firmware Update", self.firmware_update))
        self._add_wide_widget(self._create_button_row("FACTORY RESET (ESP)", self.factory_reset))

        # Spacer
        self._add_wide_widget(Widget(size_hint_y=None, height=dp_scaled(30)))

    def _add_wide_widget(self, widget):
        """Hilfsfunktion: Fügt ein Widget hinzu, das beide Spalten überspannt."""
        if hasattr(widget, 'size_hint_x'):
            widget.size_hint_x = 1
        self.body.add_widget(widget)
        # Dummy-Widget für die zweite Spalte, damit das erste Widget die volle Breite bekommt
        # (Bei Kivy GridLayouts erzwingt man so den Spalten-Übertrag)
        self.body.add_widget(Widget(size_hint_x=0, size_hint_y=None, height=0))

    def _create_section_title(self, text):
        lbl = Label(
            text=text,
            font_size=sp_scaled(15),
            bold=True,
            color=(0, 1, 0, 0.9),
            size_hint_y=None,
            height=dp_scaled(45),
            halign="left",
            valign="bottom"
        )
        lbl.bind(size=lambda *x: setattr(lbl, 'text_size', (lbl.width, None)))
        return lbl



    def _create_button_row(self, text, callback):
        btn = Button(
            text=text,
            size_hint_y=None,
            height=dp_scaled(50),
            background_normal='',
            background_color=(0.12, 0.12, 0.15, 1),
            color=(1, 1, 1, 1),
            font_size=sp_scaled(14)
        )
        btn.bind(on_release=callback)
        return btn

    # --- Actions ---
    def sync_time(self, *_): print("[GrowController] Time Sync")
    def reconnect_gateway(self, *_): print("[GrowController] Gateway Reconnect")
    def manage_sensors(self, *_): print("[GrowController] Sensors")
    def manage_ble(self, *_): print("[GrowController] BLE")
    def change_log_level(self, *_): print("[GrowController] Log Level")
    def factory_reset(self, *_): print("[GrowController] Factory Reset")
    def firmware_update(self, *_): print("[GrowController] OTA Update")

    def update_from_global(self, data):
        """Wird vom DataFlowEngine / UI Handler aufgerufen"""
        self.header.update_from_global(data)

        if not data:
            return

        # === Daten kommen als voller Device-Frame (mit adv/gatt/webserver) ===
        # Wir wollen immer die webserver-Daten für den Grow Controller
        if isinstance(data, dict):
            web_data = data.get("webserver") or data
        else:
            web_data = data

        if not web_data or not web_data.get("alive", False):
            print("[GrowController] Keine aktiven Web-Daten")
            return

        self.body.clear_widgets()

        health = web_data.get("health", {})

        # ==================== SYSTEM INFORMATION ====================
        self._add_wide_widget(self._create_section_title("SYSTEM INFORMATION"))
        self.body.add_widget(self._create_info_card("Device Name", web_data.get("dev_name", "—")))
        self.body.add_widget(self._create_info_card("Firmware",     web_data.get("fw_ver", "—")))
        self.body.add_widget(self._create_info_card("Revision",     str(web_data.get("rev", 0))))
        self.body.add_widget(self._create_info_card("WiFi Signal",  f"{health.get('signal', {}).get('rssi', '—')} dBm"))
        self.body.add_widget(self._create_info_card("Log Level",    str(web_data.get("log_level", "—"))))

        # ==================== TARGETS ====================
        self._add_wide_widget(self._create_section_title("TARGETS"))
        self.body.add_widget(self._create_info_card("Temp Min/Max", 
            f"{web_data.get('target_temp_min', '—')} – {web_data.get('target_temp_max', '—')}"))
        self.body.add_widget(self._create_info_card("Humidity Min/Max", 
            f"{web_data.get('target_humidity_min', '—')} – {web_data.get('target_humidity_max', '—')}"))
        self.body.add_widget(self._create_info_card("VPD Min/Max", 
            f"{web_data.get('target_vpd_min', '—')} – {web_data.get('target_vpd_max', '—')}"))

        # ==================== FANS ====================
        self._add_wide_widget(self._create_section_title("FANS"))
        self.body.add_widget(self._create_info_card("Exhaust Fan", 
            f"{web_data.get('exhaust_fan_pct', 0)}% ({web_data.get('exhaust_fan_rpm', 0)} RPM)"))
        self.body.add_widget(self._create_info_card("Circulation Fan", 
            f"{web_data.get('circulation_fan_pct', 0)}% ({web_data.get('circulation_fan_rpm', 0)} RPM)"))

        # ==================== LIGHT ====================
        self._add_wide_widget(self._create_section_title("LIGHT"))
        self.body.add_widget(self._create_info_card("Mode",      str(web_data.get("light_mode", "—")).upper()))
        self.body.add_widget(self._create_info_card("Power",     f"{web_data.get('light_pct', 0)}%"))
        self.body.add_widget(self._create_info_card("Remaining", f"{web_data.get('light_remaining', 0)} min"))

        # ==================== ACTIONS ====================
        self._add_wide_widget(self._create_section_title("ACTIONS"))
        self.body.add_widget(self._create_button_row("Zeit synchronisieren", self.sync_time))
        self.body.add_widget(self._create_button_row(f"Log Level: {web_data.get('log_level', 2)}", self.change_log_level))
        self.body.add_widget(self._create_button_row("Firmware Update", self.firmware_update))
        self._add_wide_widget(self._create_button_row("FACTORY RESET", self.factory_reset))

        # Spacer
        self._add_wide_widget(Widget(size_hint_y=None, height=dp_scaled(40)))

    def _create_info_card(self, label, value, val_color=(1, 1, 1, 1)):
        card = BoxLayout(orientation="vertical", size_hint_y=None, height=dp_scaled(55), padding=[dp(8), 0])
        card.add_widget(Label(text=label, font_size=sp_scaled(12), color=(0.7, 0.7, 0.7, 1), halign="left", text_size=(dp_scaled(150), None)))
        card.add_widget(Label(text=value, font_size=sp_scaled(14), bold=True, color=val_color, halign="left", text_size=(dp_scaled(150), None)))
        return card