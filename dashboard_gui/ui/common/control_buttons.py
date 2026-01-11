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

    # Dark-Pro Farben
    # Helleres, freundlicheres Schema
    COLOR_START = (0.25, 0.65, 0.25, 1)   # helleres Grün
    COLOR_STOP  = (0.75, 0.25, 0.25, 1)   # helleres Rot
    COLOR_RESET = (0.35, 0.45, 0.85, 1)   # helleres Blau
    TXT_START = "control.start"
    TXT_STOP  = "control.stop"
    TXT_RESET = "control.reset"

    def __init__(self, on_start=None, on_stop=None, on_reset=None, **kwargs):
        super().__init__(orientation="horizontal", **kwargs)

        # ----------------------------------------------------
        # LAYOUT-SCALING
        # ----------------------------------------------------
        self.spacing = dp_scaled(12)
        self.padding = [dp_scaled(12), dp_scaled(6)]
        self.size_hint_y = None
        self.height = dp_scaled(40)

        self.on_start = on_start
        self.on_stop  = on_stop
        self.on_reset = on_reset

        # ----------------------------------------------------
        #   TOGGLE BUTTON (Start/Stop)
        # ----------------------------------------------------
        self.btn_toggle = Button(
            background_down="",
            background_color=self.COLOR_START,
            markup=True,
            font_size=sp_scaled(20),
            size_hint=(0.5, 1),
            padding=[dp_scaled(10), dp_scaled(10)],
        )
        self.btn_toggle.text = (
            "[font=FA]\uf04b[/font]  " + I18N.t(self.TXT_START)
        )

        self.btn_toggle.bind(on_release=self._toggle)

        # ----------------------------------------------------
        #   RESET BUTTON
        # ----------------------------------------------------
        self.btn_reset = Button(
            background_down="",
            background_color=self.COLOR_RESET,
            markup=True,
            font_size=sp_scaled(20),
            size_hint=(0.5, 1),
            padding=[dp_scaled(10), dp_scaled(10)],
        )
        self.btn_reset.text = (
            "[font=FA]\uf021[/font]  " + I18N.t(self.TXT_RESET)
        )
        self.btn_reset.bind(on_release=lambda *_: self._trigger(self.on_reset))

        self.add_widget(self.btn_toggle)
        self.add_widget(self.btn_reset)

        # Sync zum Start
        self.sync_with_global()


    # ----------------------------------------------------
    #  Sync Button UI mit GlobalState
    # ----------------------------------------------------
    def sync_with_global(self):
        self.running = GLOBAL_STATE.running

        if self.running:
            self.btn_toggle.background_color = self.COLOR_STOP
            self.btn_toggle.text = (
                "[font=FA]\uf04d[/font]  " + I18N.t(self.TXT_STOP)
            )
        else:
            self.btn_toggle.background_color = self.COLOR_START
            self.btn_toggle.text = (
                "[font=FA]\uf04b[/font]  " + I18N.t(self.TXT_START)
            )

    # ----------------------------------------------------
    #  Button gedrückt → toggeln
    # ----------------------------------------------------
    def _toggle(self, *_):

        # STOPPED → START
        if not self.running:
            self.running = True
            self._trigger(self.on_start)

            self.btn_toggle.background_color = self.COLOR_STOP
            self.btn_toggle.text = (
                "[font=FA]\uf04d[/font]  " + I18N.t(self.TXT_STOP)
            )
            return


        # RUNNING → STOP
        else:
            self.running = False
            self._trigger(self.on_stop)

            self.btn_toggle.background_color = self.COLOR_START
            self.btn_toggle.text = (
                "[font=FA]\uf04b[/font]  " + I18N.t(self.TXT_START)
            )


    # ----------------------------------------------------
    #  GlobalState → externer UI Sync
    # ----------------------------------------------------
    def refresh_state(self, running):
        self.running = running

        if running:
            self.btn_toggle.background_color = self.COLOR_STOP
            self.btn_toggle.text = (
                "[font=FA]\uf04d[/font]  " + I18N.t(self.TXT_STOP)
            )
        else:
            self.btn_toggle.background_color = self.COLOR_START
            self.btn_toggle.text = (
                "[font=FA]\uf04b[/font]  " + I18N.t(self.TXT_START)
            )

    # ----------------------------------------------------
    # Callbacks
    # ----------------------------------------------------
    def _trigger(self, fn):
        if fn:
            fn()
