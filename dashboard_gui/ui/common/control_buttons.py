from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.properties import ObjectProperty, BooleanProperty
from kivy.graphics import Color, Rectangle
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.ui.i18n import I18N

class ControlButtons(BoxLayout):
    on_start = ObjectProperty(None, allownone=True)
    on_stop  = ObjectProperty(None, allownone=True)
    on_reset = ObjectProperty(None, allownone=True)
    running = BooleanProperty(False)

    # --- DESIGN KONFIGURATION ---
    # Hintergrund der gesamten Leiste (Schwarz-Transparent)
    BG_COLOR = (0, 0, 0, 0.6) 
    
    # Buttons (Glas Look - etwas kräftiger, damit sie auf Schwarz gut knallen)
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
        self.padding = [dp_scaled(15), dp_scaled(8)] # Etwas mehr Padding für den Background-Look
        self.size_hint_y = None
        self.height = dp_scaled(55)

        # --- NEU: SCHWARZ TRANSPARENTER HINTERGRUND ---
        with self.canvas.before:
            Color(*self.BG_COLOR)
            self.bg_rect = Rectangle(
                pos=self.pos,
                size=self.size
            )
        self.bind(pos=self._update_rect, size=self._update_rect)

        self.on_start = on_start
        self.on_stop  = on_stop
        self.on_reset = on_reset

        # 1. Start/Stop Button
        self.btn_toggle = Button(
            background_normal="",
            background_down="",
            markup=True,
            font_size=sp_scaled(16),
            size_hint=(0.5, 1)
        )

        # 2. Reset Button
        self.btn_reset = Button(
            background_normal="",
            background_down="",
            background_color=self.COLOR_RESET,
            markup=True,
            font_size=sp_scaled(16),
            size_hint=(0.5, 1),
            color=(1, 1, 1, 0.8),
            text="[font=FA]\uf021[/font]  " + I18N.t(self.TXT_RESET),
        )

        self.add_widget(self.btn_toggle)
        self.add_widget(self.btn_reset)

        self.btn_toggle.bind(on_release=self._toggle_release)
        self.btn_reset.bind(on_release=self._reset_release)

        self.sync_with_global()

    def _update_rect(self, instance, value):
        """Hält den Hintergrund synchron mit der Widget-Größe"""
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def sync_with_global(self):
        self.running = GLOBAL_STATE.graph_engine.running
        
        if self.running:
            self.btn_toggle.background_color = self.COLOR_STOP
            self.btn_toggle.text = "[font=FA]\uf04d[/font]  " + I18N.t(self.TXT_STOP)
            self.btn_toggle.color = (1, 1, 1, 0.8) # Leicht rötlicher Text
        else:
            self.btn_toggle.background_color = self.COLOR_START
            self.btn_toggle.text = "[font=FA]\uf04b[/font]  " + I18N.t(self.TXT_START)
            self.btn_toggle.color = (1, 1, 1, 0.8) # Leicht grünlicher Text



    def sync_with_global(self):
        """Synchronisiert das Aussehen der Buttons mit dem globalen Status."""
        # Wir fragen jetzt die neue Master-Engine im GSM
        self.running = GLOBAL_STATE.graph_control.is_running
        
        if self.running:
            # STOP MODUS ANZEIGEN (Wenn es läuft, zeigt der Button 'Pause')
            self.btn_toggle.background_color = self.COLOR_STOP
            self.btn_toggle.text = f"[font=FA]\uf04c[/font]  {I18N.t(self.TXT_STOP)}"
            self.btn_toggle.color = (1, 1, 1, 0.8)
        else:
            # START MODUS ANZEIGEN (Wenn es steht, zeigt der Button 'Play')
            self.btn_toggle.background_color = self.COLOR_START
            self.btn_toggle.text = f"[font=FA]\uf04b[/font]  {I18N.t(self.TXT_START)}"
            self.btn_toggle.color = (1, 1, 1, 0.8)

    def _toggle_release(self, *_):
        """Schaltet global zwischen Start und Stop um."""
        if not GLOBAL_STATE.graph_control.is_running:
            # 1. Zentrale starten
            GLOBAL_STATE.global_start()
            # 2. Optionale Callbacks (falls noch irgendwo genutzt)
            if self.on_start: self.on_start()
        else:
            # 1. Zentrale stoppen
            GLOBAL_STATE.global_stop()
            # 2. Optionale Callbacks
            if self.on_stop: self.on_stop()
        
        # 3. UI Knöpfe überall synchronisieren
        GLOBAL_STATE.sync_ui_buttons()

    def _reset_release(self, *_):
        """Löst den globalen Reset aus."""
        # Nur ein einziger Anruf beim Chef - der regelt Daten + alle Screens
        GLOBAL_STATE.global_reset()
        # Danach UI kurz refreshen
        GLOBAL_STATE.sync_ui_buttons()


    # ... Rest der Methoden bleibt gleich ...
    def refresh_state(self):
        self.sync_with_global()        