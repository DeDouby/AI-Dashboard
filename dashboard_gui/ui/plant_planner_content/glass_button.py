from kivy.uix.button import Button
from kivy.graphics import Color, Line
from datetime import date
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.scrollview import ScrollView
from kivy.properties import StringProperty
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from kivy.metrics import dp
# =============================================================================
# GLASS BUTTON
# =============================================================================

class GlassButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.background_normal = ""
        self.background_color = (0.1, 0.1, 0.15, 0.55)
        self.color = (1, 1, 1, 1)
        self.font_size = sp_scaled(18)

        self.bind(pos=self._update_canvas, size=self._update_canvas)

    def _update_canvas(self, *_):
        self.canvas.after.clear()

        with self.canvas.after:
            Color(0, 1, 0.4, 0.45)
            Line(
                rectangle=(self.x, self.y, self.width, self.height),
                width=dp(1.1)
            )


