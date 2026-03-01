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

    # Farben
    COLOR_START = (0.10, 0.30, 0.12, 1)   
    COLOR_STOP  = (0.40, 0.10, 0.10, 1)   
    COLOR_RESET = (0.12, 0.20, 0.45, 1)   

    TXT_START = "control.start"
    TXT_STOP  = "control.stop"
    TXT_RESET = "control.reset"

    def __init__(self, on_start=None, on_stop=None, on_reset=None, **kwargs):
        super().__init__(orientation="horizontal", **kwargs)

        self.spacing = dp_scaled(12)
        self.padding = [dp_scaled(12), dp_scaled(6)]
        self.size_hint_y = None
        self.height = dp_scaled(50) # Etwas höher für bessere Bedienbarkeit

        self.on_start = on_start
        self.on_stop  = on_stop
        self.on_reset = on_reset

        # Start/Stop Button
        self.btn_toggle = Button(
            background_normal="",
            background_down="",
            markup=True,
            font_size=sp_scaled(18),
            size_hint=(0.5, 1)
        )

        # Reset Button
        self.btn_reset = Button(
            background_normal="",
            background_down="",
            background_color=(*self.COLOR_RESET[:3], 0.6),
            markup=True,
            font_size=sp_scaled(18),
            size_hint=(0.5, 1),
            text="[font=FA]\uf021[/font]  " + I18N.t(self.TXT_RESET),
        )

        self.add_widget(self.btn_toggle)
        self.add_widget(self.btn_reset)

        # Binden der Events
        self.btn_toggle.bind(on_release=self._toggle_release)
        self.btn_reset.bind(on_release=self._reset_release)

        self.sync_with_global()

    def sync_with_global(self):
        """Aktualisiert die Button-Optik basierend auf GSM Status"""
        self.running = GLOBAL_STATE.running
        if self.running:
            self.btn_toggle.background_color = (*self.COLOR_STOP[:3], 0.6)
            self.btn_toggle.text = "[font=FA]\uf04d[/font]  " + I18N.t(self.TXT_STOP)
        else:
            self.btn_toggle.background_color = (*self.COLOR_START[:3], 0.6)
            self.btn_toggle.text = "[font=FA]\uf04b[/font]  " + I18N.t(self.TXT_START)

    def refresh_state(self, is_running):
        """Wird vom GSM aufgerufen, um alle Buttons systemweit zu syncen"""
        self.sync_with_global()

    def _toggle_release(self, *_):
        if not GLOBAL_STATE.running:
            GLOBAL_STATE.start()
            if self.on_start: self.on_start()
        else:
            GLOBAL_STATE.stop()
            if self.on_stop: self.on_stop()
        
        # Alle Instanzen dieser Buttons auf allen Screens aktualisieren
        GLOBAL_STATE._refresh_all_buttons()

    def _reset_release(self, *_):
        # 1. GSM Reset (Buffer löschen)
        GLOBAL_STATE.reset()
        
        # 2. Lokaler Callback (z.B. UI-Elemente explizit refreshen)
        if self.on_reset:
            self.on_reset()
        
        print("[UI] Global Reset performed")

    def _trigger(self, callback):
        if callback:
            callback()