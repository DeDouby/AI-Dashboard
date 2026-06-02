import os

from kivy.app import App
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label

from dashboard_gui.ui.scaling_utils import sp_scaled, dp_scaled
from dashboard_gui.ui.grow_overview_content.segmented_progress_bar import SegmentedProgressBar

ASSET_ROOT = os.path.join("dashboard_gui", "assets")
HUMIDIFIER_PIC = os.path.join(
    ASSET_ROOT,
    "hardware_pics",
    "humidifier.png"
)


class HumidifierTile(BoxLayout):

    def __init__(self, **kw):
        super().__init__(
            orientation="vertical",
            size_hint=(1, 1),
            **kw
        )

        self.val_box_w = dp_scaled(200)
        self.val_box_h = dp_scaled(140)

        self.padding = dp_scaled(6)
        self.spacing = dp_scaled(0)

        # ================= TITLE =================
        self.title_label = Label(
            text="Humidifier",
            font_size=sp_scaled(20),
            bold=True,
            halign="left",
            valign="middle",
            size_hint=(1, None),
            height=dp_scaled(25),
            color=(1, 1, 1, 1)
        )
        self.title_label.bind(
            size=lambda inst, *_: setattr(inst, "text_size", inst.size)
        )

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
            spacing=dp_scaled(6)
        )

        # ================= COLUMNS =================
        self.columns_box = BoxLayout(
            orientation="horizontal",
            size_hint=(1, 1),
            spacing=dp_scaled(10)
        )

        self.labels_column = BoxLayout(
            orientation="vertical",
            size_hint=(0.5, 1),
            spacing=dp_scaled(2)
        )

        self.image_column = BoxLayout(
            orientation="vertical",
            size_hint=(0.5, 1)
        )

        # ================= IMAGE =================
        self.hum_image = Image(
            source=HUMIDIFIER_PIC,
            size_hint=(1, 1),
            fit_mode="contain"
        )

        self.image_column.add_widget(self.hum_image)

        # ================= PROGRESS BAR =================
        self.prog_bar = SegmentedProgressBar()
        self.prog_bar.size_hint = (1, None)
        self.prog_bar.height = dp_scaled(18)

        # ================= CANVAS =================
        with self.value_box.canvas.before:
            Color(0, 0, 0, 0.62)
            self.value_bg = RoundedRectangle(
                radius=[dp_scaled(14)]
            )

            self.glow_color = Color(
                0.1, 0.45, 0.9, 0.35
            )
            self.value_glow = Line(width=5)

            self.border_color = Color(
                0.1, 0.45, 0.9, 0.85
            )
            self.value_border = Line(width=1.3)

        self.value_box.bind(
            pos=self._update_value_box_canvas,
            size=self._update_value_box_canvas
        )

        self.labels_column.add_widget(self.title_label) 
        # ================= LABELS =================
        self.lbl_output = Label(
            text="OUTPUT: 65%",
            font_size=sp_scaled(20),
            halign="left",
            valign="middle",
            color=(1, 1, 1, 1),
            size_hint=(1, None),
            height=dp_scaled(20)
        )

        self.lbl_live = Label(
            text="LIVE: 65%",
            font_size=sp_scaled(18),
            halign="left",
            valign="middle",
            color=(0.8, 0.8, 1, 1),
            size_hint=(1, None),
            height=dp_scaled(20)
        )

        self.lbl_status = Label(
            text="STATUS: HUMIDIFY",
            font_size=sp_scaled(18),
            halign="left",
            valign="middle",
            color=(0.9, 0.9, 0.9, 1),
            size_hint=(1, None),
            height=dp_scaled(20)
        )

        for lbl in (
            self.lbl_output,
            self.lbl_live,
            self.lbl_status
        ):
            lbl.bind(
                size=lambda inst, *_:
                setattr(inst, "text_size", inst.size)
            )
            self.labels_column.add_widget(lbl)

        # ================= BUILD =================
        self.columns_box.add_widget(self.labels_column)
        self.columns_box.add_widget(self.image_column)

        self.value_box.add_widget(self.columns_box)
        self.value_box.add_widget(self.prog_bar)

        self.content_container.add_widget(self.value_box)
        self.add_widget(self.content_container)

    def _update_box_color(self, output_pct):

        if output_pct <= 0:
            rgb = (1.0, 0.4, 0.4)

        elif output_pct < 20:
            rgb = (0.6, 0.9, 1.0)

        elif output_pct < 40:
            rgb = (0.5, 1.0, 0.9)

        elif output_pct < 60:
            rgb = (0.5, 1.0, 0.7)

        elif output_pct < 80:
            rgb = (0.9, 1.0, 0.5)

        else:
            rgb = (1.0, 0.8, 0.5)

        self.glow_color.rgba = (*rgb, 0.35)
        self.border_color.rgba = (*rgb, 0.85)

    def _update_value_box_canvas(self, obj, *args):
        self.value_bg.pos = obj.pos
        self.value_bg.size = obj.size

        rect = (
            obj.x,
            obj.y,
            obj.width,
            obj.height,
            dp_scaled(14)
        )

        self.value_glow.rounded_rectangle = rect
        self.value_border.rounded_rectangle = rect

    def update_values(self, data):
        """
        Platzhalter bis echter Humidifier existiert.
        """

        output_pct = 65
        live_pct = 65
        status = "HUMIDIFY"

        self.prog_bar.value = live_pct
        self.prog_bar.max = 100

        self.lbl_output.text = f"OUTPUT: {output_pct}%"
        self.lbl_live.text = f"LIVE: {live_pct}%"
        self.lbl_status.text = f"STATUS: {status}"

        self._update_box_color(output_pct)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        print("[DEBUG] HumidifierTile clicked")
        return True