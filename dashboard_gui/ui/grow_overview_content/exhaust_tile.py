import os

from kivy.app import App
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label

from dashboard_gui.ui.scaling_utils import sp_scaled, dp_scaled
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.overlays.exhaust_fan_overlay import ExhaustFanOverlay


ASSET_ROOT = os.path.join("dashboard_gui", "assets")
FAN_PIC = os.path.join(ASSET_ROOT, "hardware_pics", "vivosun_t6.png")
VALUE_BOX_WIDTH = dp_scaled(200)
VALUE_BOX_HEIGHT = dp_scaled(160)

class ExhaustTile(BoxLayout):

    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)

        self.padding = dp_scaled(12)
        self.spacing = dp_scaled(8)

        self.title_label = Label(
            text="Exhaust: Vivosun T6",
            font_size=sp_scaled(18),
            bold=True,
            halign="left",
            valign="middle",
            size_hint=(1, None),
            height=dp_scaled(32),
            color=(1, 1, 1, 1)
        )
        self.title_label.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))
        # remove from outer layout and add to the internal value box

        # Container für Bild und Wertebox (Horizontal)
        self.content_container = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=max(dp_scaled(100), VALUE_BOX_HEIGHT),
            spacing=dp_scaled(0)
        )

        # --------------------------------------------------
        # FAN IMAGE
        # --------------------------------------------------
        self.fan_image = Image(
            source=FAN_PIC,
            size_hint=(None, 1),
            width=dp_scaled(160)
        )
        self.content_container.add_widget(self.fan_image)

        # --------------------------------------------------
        # VALUE BOX
        # --------------------------------------------------
        self.value_box = BoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            width=VALUE_BOX_WIDTH,
            height=VALUE_BOX_HEIGHT,
            padding=[dp_scaled(10), dp_scaled(5)],
            spacing=dp_scaled(2)
        )


#            Color(0, 0, 0, 0.62)

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
        # --------------------------------------------------
        # LABELS
        # --------------------------------------------------
        self.lbl_rpm = Label(text="RPM: 0", font_size=sp_scaled(20), halign="left", valign="middle")
        self.lbl_live_speed = Label(text="LIVE: 0%", font_size=sp_scaled(20), halign="left", valign="middle")
        self.lbl_reason = Label(text="IDLE", font_size=sp_scaled(20), bold=True, halign="left", valign="middle")

        self.value_box.add_widget(self.title_label)
        for lbl in (self.lbl_rpm, self.lbl_live_speed, self.lbl_reason):
            lbl.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))
            self.value_box.add_widget(lbl)

        self.content_container.add_widget(self.value_box)
        self.add_widget(self.content_container)

    def _update_value_box_canvas(self, obj, *args):
        self.value_bg.pos = obj.pos
        self.value_bg.size = obj.size
        rect = (obj.x, obj.y, obj.width, obj.height, dp_scaled(14))
        self.value_glow.rounded_rectangle = rect
        self.value_border.rounded_rectangle = rect

    def update_values(self, data):
        rpm = int(data.get("exhaust_fan_rpm", 0))
        speed = int(data.get("exhaust_fan_speed_now", 0))
        reason = data.get("exhaust_fan_state_reason", "idle").replace("_", " ").upper()
        
        self.lbl_rpm.text = f"RPM: {rpm}"
        self.lbl_live_speed.text = f"LIVE: {speed}%"
        self.lbl_reason.text = reason

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
    
        print(f"[DEBUG] ExhaustTile clicked")
    
        overlay = ExhaustFanOverlay(parent_header=self)
        App.get_running_app().root.current_screen.add_widget(overlay)
        return True