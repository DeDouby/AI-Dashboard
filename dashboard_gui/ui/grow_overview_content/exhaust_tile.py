#exhaust_tile.py
import os

from kivy.app import App
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label

from dashboard_gui.ui.scaling_utils import sp_scaled, dp_scaled
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.overlays.exhaust_fan_overlay import ExhaustFanOverlay
from dashboard_gui.ui.grow_overview_content.segmented_progress_bar import SegmentedProgressBar

ASSET_ROOT = os.path.join("dashboard_gui", "assets")
FAN_PIC = os.path.join(ASSET_ROOT, "hardware_pics", "vivosun_t6.png")

class ExhaustTile(BoxLayout):

    def __init__(self, **kw):
        super().__init__(
            orientation="vertical",
            size_hint=(1, 1),
            **kw
        )

        self.val_box_w = dp_scaled(200)
        self.val_box_h = dp_scaled(140)

        self.padding = dp_scaled(8)
        self.spacing = dp_scaled(0)

        # ================= TITLE =================
        self.title_label = Label(
            text="Exhaust: Vivosun T6",
            font_size=sp_scaled(20),
            bold=True,
            halign="left",
            valign="middle",
            size_hint=(1, None),
            height=dp_scaled(25),
            color=(1, 1, 1, 1)
        )
        self.title_label.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))

        # ================= MAIN CONTAINER =================
        self.content_container = BoxLayout(
            orientation="horizontal",
            size_hint=(1, 1),
            spacing=dp_scaled(2)
        )

        # ================= VALUE BOX =================
        self.value_box = BoxLayout(
            orientation="vertical",
            size_hint=(1, 1),
            padding=[dp_scaled(12), dp_scaled(10)],
            spacing=dp_scaled(4)
        )

        # ================= COLUMNS =================
        self.columns_box = BoxLayout(
            orientation="horizontal",
            size_hint=(1, 1),
            spacing=dp_scaled(2)
        )

        self.labels_column = BoxLayout(
            orientation="vertical",
            size_hint=(0.6, 1),
            spacing=dp_scaled(2)
        )
        
        self.image_column = BoxLayout(
            orientation="vertical",
            size_hint=(0.4, 1)
        )
        # ================= IMAGE =================
        self.fan_image = Image(
            source=FAN_PIC,
            size_hint=(1, 1),
            fit_mode="contain"

        )
        self.image_column.add_widget(self.fan_image)

        # ================= PROGRESS BAR =================
        self.prog_bar = SegmentedProgressBar()
        self.prog_bar.size_hint = (1, None)
        self.prog_bar.height = dp_scaled(18)

        # ================= CANVAS (LIKE LIGHT TILE) =================
        with self.value_box.canvas.before:
            Color(0, 0, 0, 0.62)
            self.value_bg = RoundedRectangle(radius=[dp_scaled(14)])

            self.glow_color = Color(0.1, 0.45, 0.9, 0.35)
            self.value_glow = Line(width=5)

            self.border_color = Color(0.1, 0.45, 0.9, 0.85)
            self.value_border = Line(width=1.3)

        self.value_box.bind(pos=self._update_value_box_canvas,
                            size=self._update_value_box_canvas)

        self.labels_column.add_widget(self.title_label)

        # ================= LABELS =================
        self.lbl_rpm = Label(
            text="RPM: 0 | LIVE: 0%",
            font_size=sp_scaled(18),
            bold=True,
            halign="left",
            valign="middle",
            size_hint=(1, None),
            height=dp_scaled(18)
        )

        self.lbl_reason1 = Label(
            text="",
            font_size=sp_scaled(18),
            halign="left",
            valign="middle",
            size_hint=(1, None),
            height=dp_scaled(20)
        )
        self.lbl_reason2 = Label(
            text="",
            font_size=sp_scaled(18),
            halign="left",
            valign="middle",
            color=(0.8, 0.8, 1, 1),
            size_hint=(1, None),
            height=dp_scaled(20)
        )

        self.lbl_mode = Label(
            text="MODE: IDLE",
            font_size=sp_scaled(18),
            halign="left",
            valign="middle",
            color=(0.9, 0.9, 0.9, 1),
            size_hint=(1, None),
            height=dp_scaled(20)
        )
        self.labels_column.add_widget(self.lbl_rpm)
        self.labels_column.add_widget(self.lbl_reason1)
        self.labels_column.add_widget(self.lbl_reason2)
        self.labels_column.add_widget(self.lbl_mode)

        for lbl in (self.lbl_rpm, self.lbl_reason1, self.lbl_reason2, self.lbl_mode):
            lbl.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))
        
        # ================= BUILD =================
        # ================= BUILD =================
        
        self.columns_box.add_widget(self.labels_column)
        self.columns_box.add_widget(self.image_column)
        
        self.value_box.add_widget(self.columns_box)
        self.value_box.add_widget(self.prog_bar)
        
        self.content_container.add_widget(self.value_box)
        self.add_widget(self.content_container)


    def _update_box_color(self, rpm):
    
        if rpm is None or rpm < 0:
            rgb = (0.3, 0.3, 0.3)
    
        elif rpm <= 0:
            rgb = (1.0, 0.4, 0.4)
    
        elif rpm < 200:
            rgb = (0.6, 0.9, 1.0)
    
        elif rpm < 400:
            rgb = (0.5, 1.0, 0.9)
    
        elif rpm < 600:
            rgb = (0.5, 1.0, 0.7)
    
        elif rpm < 800:
            rgb = (0.7, 1.0, 0.5)
    
        elif rpm < 1000:
            rgb = (0.9, 1.0, 0.5)
    
        elif rpm < 1200:
            rgb = (1.0, 1.0, 0.6)
    
        elif rpm < 1400:
            rgb = (1.0, 0.9, 0.5)
    
        elif rpm < 1600:
            rgb = (1.0, 0.8, 0.5)
    
        elif rpm < 1800:
            rgb = (1.0, 0.7, 0.5)
    
        else:
            rgb = (1.0, 0.6, 0.5)
    
        self.glow_color.rgba = (*rgb, 0.35)
        self.border_color.rgba = (*rgb, 0.85)

    def _update_value_box_canvas(self, obj, *args):
        self.value_bg.pos = obj.pos
        self.value_bg.size = obj.size
        rect = (obj.x, obj.y, obj.width, obj.height, dp_scaled(14))
        self.value_glow.rounded_rectangle = rect
        self.value_border.rounded_rectangle = rect

    def update_values(self, data):
        rpm = int(data.get("exhaust_fan_rpm", 0))
        speed = int(data.get("exhaust_fan_speed_now", 0))
        reason1 = str(data.get("exhaust_fan_state_reason_1", "")).replace('_', ' ').upper()
        reason2 = str(data.get("exhaust_fan_state_reason_2", "")).replace('_', ' ').upper()

        self.prog_bar.value = speed
        self.prog_bar.max = 100
    
        self.lbl_rpm.text = f"RPM: {rpm} | LIVE: {speed}%"
        # === FIX FÜR STATUS LABEL ===
        self.lbl_reason1.text = reason1
        self.lbl_reason2.text = reason2
        chaos = bool(data.get("exhaust_fan_chaos_active", False))
        night = bool(data.get("exhaust_fan_night_reduction", False))
        manual = bool(data.get("exhaust_fan_manual_control", False))
        
        reason = str(data.get("exhaust_fan_state_reason_1", "")).lower()

        if chaos:
            mode = "CHAOS"
        elif night:
            mode = "NIGHT"
    
        elif manual:
            mode = "MANUAL"
        elif reason.startswith("hum"):
            mode = "HUMIDITY"
        elif reason.startswith("temp"):
            mode = "TEMP"
        
        else:
            mode = "UNKNOWN"
        
        self.lbl_mode.text = f"MODE: {mode}"    
        self._update_box_color(rpm)


    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
    
        print(f"[DEBUG] ExhaustTile clicked")
    
        overlay = ExhaustFanOverlay(parent_header=self)
        App.get_running_app().root.current_screen.add_widget(overlay)
        return True