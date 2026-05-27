import os
from kivy.app import App
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label

from dashboard_gui.ui.scaling_utils import sp_scaled, dp_scaled
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.formatters import UIFormatter
ASSET_ROOT = os.path.join("dashboard_gui", "assets")
SHT31_PIC = os.path.join(ASSET_ROOT, "hardware_pics", "sht31.png")
# VALUE BOX SIZE
VALUE_BOX_WIDTH = dp_scaled(180)
VALUE_BOX_HEIGHT = dp_scaled(140)
class SensorInternalSHT31Tile(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)
        self.padding = dp_scaled(10)
        self.spacing = dp_scaled(6)

        self.title_label = Label(
            text="Internal: SHT31",
            font_size=sp_scaled(20),
            bold=True,
            halign="left",
            valign="middle",
            size_hint=(1, None),
            height=dp_scaled(32),
            color=(1, 1, 1, 1)
        )
        self.title_label.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))

        self.content_container = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=max(dp_scaled(100), VALUE_BOX_HEIGHT),
            spacing=dp_scaled(10)
        )

        # IMAGE
        self.sensor_image = Image(
            source=SHT31_PIC,
            size_hint=(None, 1),
            width=dp_scaled(120)
        )
        self.content_container.add_widget(self.sensor_image)

        # VALUE BOX
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
            self.value_bg = RoundedRectangle(radius=[dp_scaled(14)])
            Color(0.2, 0.8, 0.2, 0.4) # Grünlicher Ton für Sensoren
            self.value_glow = Line(width=5)
            Color(0.2, 0.8, 0.2, 0.8)
            self.value_border = Line(width=1.3)

        self.value_box.bind(pos=self._update_canvas, size=self._update_canvas)

        # LABELS
        self.lbl_temp = Label(
            text="--",
            markup=True,
            font_size=sp_scaled(20)
        )
        
        self.lbl_hum = Label(
            text="--",
            markup=True,
            font_size=sp_scaled(20)
        )
        
        self.lbl_vpd = Label(
            text="--",
            markup=True,
            font_size=sp_scaled(20)
        )

        for lbl in (self.title_label, self.lbl_temp, self.lbl_hum, self.lbl_vpd):
            lbl.halign = "left"
            lbl.valign = "middle"
            lbl.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))
            self.value_box.add_widget(lbl)

        self.content_container.add_widget(self.value_box)
        self.add_widget(self.content_container)

    def _update_canvas(self, obj, *args):
        self.value_bg.pos = obj.pos
        self.value_bg.size = obj.size
        rect = (obj.x, obj.y, obj.width, obj.height, dp_scaled(14))
        self.value_glow.rounded_rectangle = rect
        self.value_border.rounded_rectangle = rect

    def update_values(self, data):
        internal = data.get("internal", {})
    
        temp_data = internal.get("temperature", {})
        hum_data  = internal.get("humidity", {})
        vpd_data  = data.get("vpd_internal", {})
    
        temp_val = temp_data.get("value")
        hum_val  = hum_data.get("value")
        vpd_val  = vpd_data.get("value")
    
        temp_unit = temp_data.get("unit", "")
        hum_unit  = hum_data.get("unit", "")
        vpd_unit  = vpd_data.get("unit", "")
    
        trend_temp = GLOBAL_STATE.get_trend_icon("temp_in")
        trend_hum  = GLOBAL_STATE.get_trend_icon("hum_in")
        trend_vpd  = GLOBAL_STATE.get_trend_icon("vpd_in")
    
        self.lbl_temp.text = UIFormatter.format_sensor_label(
            name="Temp",
            value=temp_val if temp_val is not None else "--",
            unit=temp_unit,
            trend=trend_temp,
            sz_val=20,
            sz_name=12,
            sz_trend=16,
            sz_unit=12
        )
    
        self.lbl_hum.text = UIFormatter.format_sensor_label(
            name="Hum",
            value=hum_val if hum_val is not None else "--",
            unit=hum_unit,
            trend=trend_hum,
            sz_val=20,
            sz_name=12,
            sz_trend=16,
            sz_unit=12
        )
    
        self.lbl_vpd.text = UIFormatter.format_sensor_label(
            name="VPD",
            value=vpd_val if vpd_val is not None else "--",
            unit=vpd_unit,
            trend=trend_vpd,
            sz_val=20,
            sz_name=12,
            sz_trend=16,
            sz_unit=12
        )