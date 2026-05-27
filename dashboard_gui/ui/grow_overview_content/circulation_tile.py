import os
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.app import App
from kivy.graphics import Color, RoundedRectangle, Line

from dashboard_gui.ui.scaling_utils import sp_scaled, dp_scaled
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.overlays.circulation_fan_overlay import CirculationFanOverlay

ASSET_ROOT = os.path.join("dashboard_gui", "assets")
CIRC_PIC = os.path.join(ASSET_ROOT, "hardware_pics", "mars_gaming.png")
VALUE_BOX_WIDTH = dp_scaled(200)
VALUE_BOX_HEIGHT = dp_scaled(140)
class CirculationTile(BoxLayout):

    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)
        self.padding = dp_scaled(12)
        self.spacing = dp_scaled(8)
        self.title_label = Label(
            text="Mars Gaming PWMX",
            font_size=sp_scaled(18),
            bold=True,
            halign="left",
            valign="middle",
            size_hint=(1, None),
            height=dp_scaled(32),
            color=(1, 1, 1, 1)
        )
        self.title_label.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))
        # Container für Bild und Wertebox (Horizontal)
        self.content_container = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=max(dp_scaled(100), VALUE_BOX_HEIGHT),
            spacing=dp_scaled(2)
        )

        # ---------------- IMAGE ----------------
        self.fan_image = Image(
            source=CIRC_PIC,
            size_hint=(None, 1),
            width=dp_scaled(160)
        )
        self.content_container.add_widget(self.fan_image)

        # ---------------- VALUE BOX ----------------
        self.value_box = BoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            width=VALUE_BOX_WIDTH,
            height=VALUE_BOX_HEIGHT,
            padding=[dp_scaled(10), dp_scaled(5)],
            spacing=dp_scaled(2)
        )

        with self.value_box.canvas.before:
            Color(0, 0, 0, 0.62)
            self.value_bg = RoundedRectangle(
                pos=self.value_box.pos,
                size=self.value_box.size,
                radius=[dp_scaled(14)]
            )
            Color(0.1, 0.45, 0.9, 0.35)
            self.value_glow = Line(width=5)
            
            Color(0.1, 0.45, 0.9, 0.85)
            self.value_border = Line(width=1.3)
        
        self.value_box.bind(
            pos=self._update_value_box_canvas,
            size=self._update_value_box_canvas
        )
        
        # ---------------- LABELS ----------------
        self.lbl_rpm = Label(text="RPM: 0", font_size=sp_scaled(20), halign="left", valign="middle")
        self.lbl_live_speed = Label(text="LIVE: 0%", font_size=sp_scaled(20), halign="left", valign="middle")
        self.lbl_status = Label(text="IDLE", font_size=sp_scaled(20), halign="left", valign="middle")

        self.value_box.add_widget(self.title_label)
        for lbl in (self.lbl_rpm, self.lbl_live_speed, self.lbl_status):
            lbl.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))
            self.value_box.add_widget(lbl)

        # Container zusammenbauen
        self.content_container.add_widget(self.value_box)
        self.add_widget(self.content_container)

    # ---------------- CANVAS UPDATE ----------------
    def _update_value_box_canvas(self, obj, *args):
        x, y = obj.pos
        w, h = obj.size
        r = dp_scaled(14)
        rect = (x, y, w, h, r)

        self.value_bg.pos = (x, y)
        self.value_bg.size = (w, h)
        self.value_glow.rounded_rectangle = rect
        self.value_border.rounded_rectangle = rect

    # ---------------- DATA UPDATE ----------------
    def update_values(self, data):
        rpm = int(data.get('circulation_fan_rpm', 0))
        speed = int(data.get('circulation_fan_speed_now', 0))

        self.lbl_rpm.text = f"RPM: {rpm}"
        self.lbl_live_speed.text = f"LIVE: {speed}%"
        self.lbl_status.text = "ACTIVE" if speed > 0 else "IDLE"

    # ---------------- TOUCH ----------------
    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
    
        print(f"[DEBUG] CirculationTile clicked")
    
        ui = GLOBAL_STATE.ui_handler
        if getattr(ui, "active_circulation_fan_overlay", None):
            ui.active_circulation_fan_overlay.close()
    
        overlay = CirculationFanOverlay(parent_header=self)
        ui.active_circulation_fan_overlay = overlay
        App.get_running_app().root.current_screen.add_widget(overlay)
        return True