from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.label import Label

from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.global_state_manager import GLOBAL_STATE

# Overlay import (kommt gleich)
from dashboard_gui.ui.common.fan_overlay import FanOverlay


class IconLabel(Label):
    def __init__(self, **kw):
        kw.setdefault("font_name", "FA")
        kw.setdefault("font_size", sp_scaled(22))
        kw.setdefault("halign", "center")
        kw.setdefault("valign", "middle")
        super().__init__(**kw)
        self.bind(size=lambda *_: self.texture_update())


class CirculationFanControl(BoxLayout):
    def __init__(self, parent_header=None, **kw):
        super().__init__(**kw)

        self.parent_header = parent_header
        self.orientation = "horizontal"
        self.spacing = dp_scaled(2)
        self.size_hint = (None, 1)
        self.width = dp_scaled(45)

        self.icon = IconLabel(text="\uf863", font_size=sp_scaled(20))
        self.add_widget(self.icon)

        self.set_rpm(0)

    # -----------------------
    # CLICK → OPEN OVERLAY
    # -----------------------
    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False

        ui = GLOBAL_STATE.ui_handler

        if getattr(ui, "active_fan_overlay", None):
            ui.active_fan_overlay.close()
            ui.active_fan_overlay = None
        else:
            overlay = FanOverlay(parent_header=self.parent_header)
            ui.active_fan_overlay = overlay

            from kivy.app import App
            App.get_running_app().root.current_screen.add_widget(overlay)

        return True

    # -----------------------
    # VISUAL
    # -----------------------
    def set_rpm(self, rpm):
        try:
            val = float(rpm) if rpm is not None else 0
        except:
            val = 0

        if val > 100:
            self.icon.color = (0.3, 1, 0.3, 1)
        else:
            self.icon.color = (1, 0.2, 0.2, 1)