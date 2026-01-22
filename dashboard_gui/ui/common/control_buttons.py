from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.properties import ObjectProperty, BooleanProperty

from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.ui.i18n import I18N


class ControlButtons(BoxLayout):

    on_start = ObjectProperty(None, allownone=True)
    on_stop  = ObjectProperty(None, allownone=True)
    on_reset = ObjectProperty(None, allownone=True)
    running = BooleanProperty(False)

    # Ultra Dark Look
    COLOR_START = (0.10, 0.30, 0.12, 1)   # sehr dunkles Grün
    COLOR_STOP  = (0.40, 0.10, 0.10, 1)   # sehr dunkles Rot
    COLOR_RESET = (0.12, 0.20, 0.45, 1)   # sehr dunkles Blau

    TXT_START = "control.start"
    TXT_STOP  = "control.stop"
    TXT_RESET = "control.reset"

    def __init__(self, on_start=None, on_stop=None, on_reset=None, **kwargs):
        super().__init__(orientation="horizontal", **kwargs)

        self.spacing = dp_scaled(12)
        self.padding = [dp_scaled(12), dp_scaled(6)]
        self.size_hint_y = None
        self.height = dp_scaled(40)

        self.on_start = on_start
        self.on_stop  = on_stop
        self.on_reset = on_reset

        # --------------------------
        # Toggle Button
        # --------------------------
        self.btn_toggle = Button(
            background_normal="",
            background_down="",
            background_color=(*self.COLOR_START[:3], 0.6),
            markup=True,
            font_size=sp_scaled(20),
            size_hint=(0.5, 1),
            padding=[dp_scaled(10), dp_scaled(10)],
            text="[font=FA]\uf04b[/font]  " + I18N.t(self.TXT_START),
        )

        # --------------------------
        # Reset Button
        # --------------------------
        self.btn_reset = Button(
            background_normal="",
            background_down="",
            background_color=(*self.COLOR_RESET[:3], 0.6),
            markup=True,
            font_size=sp_scaled(20),
            size_hint=(0.5, 1),
            padding=[dp_scaled(10), dp_scaled(10)],
            text="[font=FA]\uf021[/font]  " + I18N.t(self.TXT_RESET),
        )

        self.add_widget(self.btn_toggle)
        self.add_widget(self.btn_reset)

        # --------------------------
        # Bind Press/Release → Transparenz
        # --------------------------
        for btn, base_color, callback in [
            (self.btn_toggle, self.COLOR_START, self._toggle_release),
            (self.btn_reset, self.COLOR_RESET, self._reset_release),
        ]:
            btn.bind(
                on_press=lambda b, c=base_color: self._press(b, c),
                on_release=lambda b, cb=callback, c=base_color: self._release(b, c, cb)
            )

        self.sync_with_global()

    # --------------------------
    # Press / Release Methods
    # --------------------------
    def _press(self, btn, base_color):
        r, g, b, _ = base_color
        btn.background_color = (r, g, b, 0.75)

    def _release(self, btn, base_color, callback):
        r, g, b, _ = base_color
        btn.background_color = (r, g, b, 0.6)
        callback(btn)

    def _toggle_release(self, *_):
        self._toggle()

    def _reset_release(self, *_):
        self._trigger(self.on_reset)

    # --------------------------
    # Sync mit GlobalState
    # --------------------------
    def sync_with_global(self):
        self.running = GLOBAL_STATE.running
        if self.running:
            self.btn_toggle.background_color = (*self.COLOR_STOP[:3], 0.6)
            self.btn_toggle.text = "[font=FA]\uf04d[/font]  " + I18N.t(self.TXT_STOP)
        else:
            self.btn_toggle.background_color = (*self.COLOR_START[:3], 0.6)
            self.btn_toggle.text = "[font=FA]\uf04b[/font]  " + I18N.t(self.TXT_START)

    # --------------------------
    # Toggle Logic
    # --------------------------
    def _toggle(self, *_):
        if not self.running:
            self.running = True
            self._trigger(self.on_start)
            self.btn_toggle.background_color = (*self.COLOR_STOP[:3], 0.6)
            self.btn_toggle.text = "[font=FA]\uf04d[/font]  " + I18N.t(self.TXT_STOP)
        else:
            self.running = False
            self._trigger(self.on_stop)
            self.btn_toggle.background_color = (*self.COLOR_START[:3], 0.6)
            self.btn_toggle.text = "[font=FA]\uf04b[/font]  " + I18N.t(self.TXT_START)

    # --------------------------
    # Externe UI Sync
    # --------------------------
    def refresh_state(self, running):
        self.running = running
        self.sync_with_global()

    # --------------------------
    # Callback
    # --------------------------
    def _trigger(self, fn):
        if fn:
            fn()
