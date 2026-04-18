from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.clock import Clock
import time
import config
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.overlays.lock_overlay import LockOverlay
from dashboard_gui.overlays.unified_slider import UnifiedSlider


class BaseOverlay(FloatLayout):
    """Gemeinsame Basis für alle Geräte-Overlays (Fan, Exhaust, Light)"""

    def __init__(self, title, command_type, **kwargs):
        super().__init__(**kwargs)
        
        self.title = title
        self.command_type = command_type          # z.B. "circulation_fan"
        self._last_sent_rev = 0
        self._last_user_action = time.time()
        self._user_active = False
        self._ui_lock = False
        self._init_done = False
        self._locked = True
        self._target_state = {}                   # wird in Child gefüllt

        # Hintergrund + Panel (gemeinsam)
        self._build_ui()

        self._update_event = Clock.schedule_interval(self.update_ui, 1.0)
        self._sync_event = Clock.schedule_interval(self._sync_check, 1.2)

        Clock.schedule_once(self._init_values, 0.2)

    def _build_ui(self):
        # ... hier kommt der komplette Aufbau (Panel, Titel, Sync-Icon, Slider-Bereich, etc.)
        # Ich kann dir den vollständigen Code geben, wenn du willst.
        pass

    # === Gemeinsame Methoden ===
    def _set_orange(self):
        self.sync_icon.text = "[font=FA]\uf021[/font]"
        self.sync_icon.color = (1, 0.5, 0, 1)

    def _set_green(self):
        self.sync_icon.text = "[font=FA]\uf058[/font]"
        self.sync_icon.color = (0, 1, 0, 1)

    def _send_command(self, **extra_kwargs):
        """Einheitlicher Weg zum Senden"""
        payload = {**self._target_state, **extra_kwargs}
        new_rev = GLOBAL_STATE.send_overlay_command(self.command_type, **payload)
        
        if new_rev:
            self._last_sent_rev = new_rev
            self._last_user_action = time.time()
            self._set_orange()

    def update_ui(self, *_):
        # Die wasserdichte Sync-Logik, die wir schon haben
        # ...
        pass

    # Weitere gemeinsame Methoden: _touch_down, _touch_up, _on_slider_change, etc.