import os
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Rectangle, Color, Line
from kivy.clock import Clock
from kivy.metrics import dp
from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.global_state_manager import GLOBAL_STATE

ASSET_ROOT = os.path.join("dashboard_gui", "assets")

class GlassButton(Button):
    """Ein Button mit modernem, durchscheinendem Rahmen-Look"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0.1, 0.1, 0.1, 0.5)  # Halbdurchsichtig
        self.color = (1, 1, 1, 1)
        self.bind(pos=self.update_canvas, size=self.update_canvas)

    def update_canvas(self, *args):
        self.canvas.after.clear()
        with self.canvas.after:
            Color(0, 1, 0, 0.6)  # Dezenter grüner Rahmen (passend zum Hanf)
            Line(rectangle=(self.x, self.y, self.width, self.height), width=dp(1.2))

class GrowControllerScreen(Screen):
    name = "grow_controller"
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        GLOBAL_STATE.ui_handler.attach_screen("grow_controller", self)
        self.root = BoxLayout(orientation="vertical")

        # Hintergrund Setup
        with self.root.canvas.before:
            # Dunkler Layer damit das Bild nicht zu hell ist
            Color(0, 0, 0, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            # Das geile Bild
            Color(1, 1, 1, 0.7) # 70% Sichtbarkeit für bessere Lesbarkeit der Schrift
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

        # Scrollview
        self.scroll = ScrollView(do_scroll_x=False, bar_width=dp(8))
        self.body = GridLayout(
            cols=2,
            size_hint_y=None,
            padding=dp_scaled(20),
            spacing=dp_scaled(15), # Bisschen mehr Platz zum Atmen
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

    def _add_wide_widget(self, widget):
        widget.size_hint_x = 1
        self.body.add_widget(widget)
        self.body.add_widget(Widget(size_hint_x=0, size_hint_y=None, height=0))

    def _create_section_title(self, text):
        return Label(
            text=text.upper(),
            font_size=sp_scaled(16),
            bold=True,
            color=(0, 1, 0.2, 1), # Giftiges Grün
            size_hint_y=None,
            height=dp_scaled(50),
            halign="left",
            valign="middle",
            text_size=(dp_scaled(350), None)
        )

    def _create_info_card(self, label, value, val_color=(1, 1, 1, 1)):
        # Card mit eigenem Hintergrund-Rechteck für Lesbarkeit
        card = BoxLayout(orientation="vertical", size_hint_y=None, height=dp_scaled(60), padding=[dp(10), dp(5)])
        with card.canvas.before:
            Color(0, 0, 0, 0.6) # Schwarzer Glas-Effekt
            card.bg = Rectangle(pos=card.pos, size=card.size)
        card.bind(pos=lambda s, v: setattr(card.bg, 'pos', v), size=lambda s, v: setattr(card.bg, 'size', v))
        
        card.add_widget(Label(text=label, font_size=sp_scaled(11), color=(0.8, 0.8, 0.8, 1), halign="left", text_size=(dp_scaled(150), None)))
        card.add_widget(Label(text=str(value), font_size=sp_scaled(15), bold=True, color=val_color, halign="left", text_size=(dp_scaled(150), None)))
        return card

    def build_ui(self, *_):
        self.body.clear_widgets()

        # SYSTEM INFO
        self._add_wide_widget(self._create_section_title("Hardware Status"))
        self.body.add_widget(self._create_info_card("ESP32-S3 Core", "v2.4.1"))
        self.body.add_widget(self._create_info_card("Uptime", "14d 07:23"))
        self.body.add_widget(self._create_info_card("WiFi Signal", "-68 dBm", (0, 1, 0, 1)))
        self.body.add_widget(self._create_info_card("Node IP", "192.168.2.39"))

        # ACTIONS
        self._add_wide_widget(self._create_section_title("Control Panel"))
        self.body.add_widget(GlassButton(text="Sync Clock", on_release=self.sync_time, height=dp_scaled(55), size_hint_y=None))
        self.body.add_widget(GlassButton(text="OTA Update", on_release=self.firmware_update, height=dp_scaled(55), size_hint_y=None))
        
        reset_btn = GlassButton(text="FACTORY RESET", on_release=self.factory_reset, height=dp_scaled(55), size_hint_y=None)
        reset_btn.color = (1, 0.2, 0.2, 1) # Warnungs-Rot
        self._add_wide_widget(reset_btn)

    def sync_time(self, *_): print("Syncing...")
    def firmware_update(self, *_): print("Update...")
    def factory_reset(self, *_): print("Reset...")
    def update_from_global(self, data):
        """Hier kommen später die Live-Daten hin (ohne clear_widgets!)"""
        self.header.update_from_global(data)
        if not data:
            return
        print("[GrowController] Update received")   # erstmal nur zum Testen