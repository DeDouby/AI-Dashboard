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
MLX90614_PIC = os.path.join(ASSET_ROOT, "hardware_pics", "mlx90614.png")

# VALUE BOX SIZE


class SensorExternalMLX90614Tile(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)
        self.val_box_w = dp_scaled(200)
        self.val_box_h = dp_scaled(140)

        self.padding = dp_scaled(10)
        self.spacing = dp_scaled(6)

        self.title_label = Label(
            text="Leaf Temp: MLX90614",
            font_size=sp_scaled(20),
            bold=True,
            halign="left",
            valign="middle",
            size_hint=(1, None),
            height=dp_scaled(50),
            color=(1, 1, 1, 1)
        )
        self.title_label.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))

        self.content_container = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=max(dp_scaled(100), self.val_box_h),
            spacing=dp_scaled(2)
        )

        # IMAGE
        self.sensor_image = Image(
            source=MLX90614_PIC,
            height=dp_scaled(120),
            allow_stretch=True,
            keep_ratio=True
        )
        self.content_container.add_widget(self.sensor_image)

        # VALUE BOX
        self.value_box = BoxLayout(
            orientation="vertical",
            size_hint=(1, None), # <--- ÄNDERE ZU 1 (statt None)
            # Entferne width=VALUE_BOX_WIDTH komplett!
            height=dp_scaled(140),
            padding=[dp_scaled(10), dp_scaled(5)],
            spacing=dp_scaled(2)
        )


        with self.value_box.canvas.before:
            Color(0, 0, 0, 0.62)
            self.value_bg = RoundedRectangle(radius=[dp_scaled(14)])
            Color(0.2, 0.8, 0.2, 0.4)   # Grünlicher Sensor-Ton
            self.value_glow = Line(width=5)
            Color(0.2, 0.8, 0.2, 0.8)
            self.value_border = Line(width=1.3)

        self.value_box.bind(pos=self._update_canvas, size=self._update_canvas)

        # LABELS
        self.lbl_leaf_temp = Label(
            text="--",
            markup=True,
            font_size=sp_scaled(20)
        )
        
        self.lbl_vpd_leaf = Label(
            text="--",
            markup=True,
            font_size=sp_scaled(20)
        )

        for lbl in (self.title_label, self.lbl_leaf_temp, self.lbl_vpd_leaf):
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
    
    def update_values(self, data, prefix=""):
        external2 = data.get("external2", {})
    
        leaf_temp_data = external2.get("leaf_temp", {})
        vpd_leaf_data  = external2.get("vpd_leaf", {})

        leaf_temp_val = leaf_temp_data.get("value")
        vpd_leaf_val  = vpd_leaf_data.get("value") if isinstance(vpd_leaf_data, dict) else vpd_leaf_data

        leaf_temp_unit = leaf_temp_data.get("unit", "°C")
        vpd_leaf_unit  = vpd_leaf_data.get("unit", "kPa") if isinstance(vpd_leaf_data, dict) else "kPa"

        # Trend Icons
        key_prefix = f"{prefix}_" if prefix else ""
        
        trend_temp = GLOBAL_STATE.get_trend_icon(f"{key_prefix}leaf_temp")
        trend_vpd  = GLOBAL_STATE.get_trend_icon(f"{key_prefix}vpd_leaf")

        self.lbl_leaf_temp.text = UIFormatter.format_sensor_label(
            name="Leaf",
            value=leaf_temp_val if leaf_temp_val is not None else "--",
            unit=leaf_temp_unit,
            trend=trend_temp,
            sz_val=20, sz_name=12, sz_trend=16, sz_unit=12
        )

        self.lbl_vpd_leaf.text = UIFormatter.format_sensor_label(
            name="VPD Leaf",
            value=vpd_leaf_val if vpd_leaf_val is not None else "--",
            unit=vpd_leaf_unit,
            trend=trend_vpd,
            sz_val=20, sz_name=12, sz_trend=16, sz_unit=12
        )