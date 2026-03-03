# dashboard_gui/ui/common/broadcast_button.py

from kivy.uix.button import Button
from kivy.clock import Clock
from dashboard_gui.ui.scaling_utils import sp_scaled
import core


class BroadcastButton(Button):
    """
    Eigenständiges Modul für Broadcast Control.
    Kein Logik-Code im Header mehr.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.font_name = "FA"
        self.font_size = sp_scaled(22)
        self.size_hint = (0.08, 1)

        self.background_color = (0, 0, 0, 0)
        self.color = (0.7, 0.7, 0.7, 1)

        self.bind(on_release=self._toggle)

        self._refresh_event = Clock.schedule_interval(self._refresh_state, 2)

        self._refresh_state()

    # -------------------------------------------------

    def _toggle(self, *_):
        from dashboard_gui.global_state_manager import GLOBAL_STATE
    
        if GLOBAL_STATE.get_broadcast_active():
            # User will stoppen
            core.stop_broadcast_bridge()
            GLOBAL_STATE.set_broadcast_active(False)
            GLOBAL_STATE.set_broadcast_user_disabled(True)
        else:
            # User will starten
            core.start_broadcast_bridge()
            GLOBAL_STATE.set_broadcast_active(True)
            GLOBAL_STATE.set_broadcast_user_disabled(False)
    
        GLOBAL_STATE.refresh_all_headers()
        self._refresh_state()

    # -------------------------------------------------

    def _refresh_state(self, *_):
        from dashboard_gui.global_state_manager import GLOBAL_STATE

        available = bool(GLOBAL_STATE.broadcast_data_available)
        active = GLOBAL_STATE.get_broadcast_active()

        if not available:
            self.disabled = True
            self.color = (0.5, 0.5, 0.5, 1)
            self.text = "\uf071"
            return

        self.disabled = False

        if active:
            self.text = "\uf09e"
            self.color = (0.3, 1, 0.3, 1)
        else:
            self.text = "\uf05e"
            self.color = (0.7, 0.7, 0.7, 1)

    # -------------------------------------------------

    def on_parent(self, *_):
        """Cleanup wenn entfernt"""
        if not self.parent:
            self._refresh_event.cancel()