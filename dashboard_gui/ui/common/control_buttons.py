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

    # --- DESIGN KONFIGURATION (15% Glass Look) ---
    COLOR_START = (0.2, 0.8, 0.2, 0.15) # Dezent Grün
    COLOR_STOP  = (0.8, 0.2, 0.2, 0.15) # Dezent Rot
    COLOR_RESET = (0.2, 0.4, 0.9, 0.15) # Dezent Blau

    TXT_START = "control.start"
    TXT_STOP  = "control.stop"
    TXT_RESET = "control.reset"

    def __init__(self, on_start=None, on_stop=None, on_reset=None, **kwargs):
        super().__init__(orientation="horizontal", **kwargs)

        # Layout-Setup
        self.spacing = dp_scaled(12)
        self.padding = [dp_scaled(12), dp_scaled(6)]
        self.size_hint_y = None
        self.height = dp_scaled(50)

        self.on_start = on_start
        self.on_stop  = on_stop
        self.on_reset = on_reset

        # 1. Start/Stop Button (Umschaltbar)
        self.btn_toggle = Button(
            background_normal="",
            background_down="",
            markup=True,
            font_size=sp_scaled(16),
            size_hint=(0.5, 1)
        )

        # 2. Reset Button (Statisch)
        self.btn_reset = Button(
            background_normal="",
            background_down="",
            background_color=self.COLOR_RESET,
            markup=True,
            font_size=sp_scaled(16),
            size_hint=(0.5, 1),
            color=(1, 1, 1, 0.7), # Text leicht transparent für Glass-Look
            text="[font=FA]\uf021[/font]  " + I18N.t(self.TXT_RESET),
        )

        # Widgets hinzufügen
        self.add_widget(self.btn_toggle)
        self.add_widget(self.btn_reset)

        # Binden der Events
        self.btn_toggle.bind(on_release=self._toggle_release)
        self.btn_reset.bind(on_release=self._reset_release)

        # Initiale Optik setzen
        self.sync_with_global()

    def sync_with_global(self):
        """Aktualisiert die Button-Optik basierend auf dem GSM Status"""
        self.running = GLOBAL_STATE.graph_engine.running
        
        if self.running:
            # STOP Modus
            self.btn_toggle.background_color = self.COLOR_STOP
            self.btn_toggle.text = "[font=FA]\uf04d[/font]  " + I18N.t(self.TXT_STOP)
            self.btn_toggle.color = (1, 1, 1, 0.7) # Rötlicher Schimmer
        else:
            # START Modus
            self.btn_toggle.background_color = self.COLOR_START
            self.btn_toggle.text = "[font=FA]\uf04b[/font]  " + I18N.t(self.TXT_START)
            self.btn_toggle.color = (1, 1, 1, 0.7) # Grünlicher Schimmer

    def refresh_state(self):
        self.sync_with_global()

    def _toggle_release(self, *_):
        """Logik für Start/Stop"""
        if not GLOBAL_STATE.graph_engine.running:
            GLOBAL_STATE.graph_engine.start()
            if self.on_start: self.on_start()
        else:
            GLOBAL_STATE.graph_engine.stop()
            if self.on_stop: self.on_stop()
        
        # Alle Instanzen dieser Buttons im UI synchronisieren
        GLOBAL_STATE.sync_ui_buttons()

    def _reset_release(self, *_):
        """Logik für Reset"""
        GLOBAL_STATE.graph_engine.reset()
        if self.on_reset: self.on_reset()
        
        # Alle Instanzen synchronisieren
        GLOBAL_STATE.sync_ui_buttons()