###############################################################################
# ZENTRALE LOCK-OVERLAY IMPLEMENTIERUNG
# Eliminiert Duplikation und erzwingt konsistente Lock-Behavior
###############################################################################

from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled


class LockOverlay:
    """
    Verwaltung der dezenten Sperr-Maske und des UNLOCK-Buttons.
    
    Wird von CirculationFanOverlay, ExhaustFanOverlay und LightOverlay verwendet.
    
    Zentrale Logik:
    - overlay: Button mit transparentem Hintergrund über dem Panel
    - unlock_button: "UNLOCK TO EDIT" Button unten links
    - Position wird mit Panel-Bewegung synchronisiert
    """
    
    def __init__(self, parent, panel, unlock_callback):
        """
        Args:
            parent: FloatLayout (das Hauptwidget/Overlay)
            panel: BoxLayout (das Panel das gesperrt werden soll)
            unlock_callback: Funktion die aufgerufen wird wenn entsperrt wird
        """
        self.parent = parent
        self.panel = panel
        self.unlock_callback = unlock_callback
        self.overlay = None
        self.unlock_button = None

    def create(self):
        """Erstellt die Lock-Maske + Unlock-Button über dem Panel."""
        if self.overlay:
            return  # Already created

        # === TRANSPARENTE SPERR-MASKE ===
        self.overlay = Button(
            background_color=(0, 0, 0, 0.09),  # Quasi-unsichtbar
            size=self.panel.size,
            pos=self.panel.pos,
            size_hint=(None, None)
        )

        # === UNLOCK-BUTTON ===
        self.unlock_button = Button(
            text="UNLOCK TO EDIT",
            size_hint=(None, None),
            size=(dp_scaled(200), dp_scaled(50)),
            pos_hint={'x': 0.04, 'y': 0.04},  # Unten links im Hauptwidget
            background_color=(0.05, 0.55, 0.95, 0.95),
            color=(1, 1, 1, 1),
            bold=True,
            font_size=sp_scaled(15.5)
        )
        self.unlock_button.bind(on_release=self._on_unlock)

        # === ASSEMBLY ===
        self.overlay.add_widget(self.unlock_button)
        self.parent.add_widget(self.overlay)

        # === POSITION SYNCHRONISIERUNG ===
        self.panel.bind(pos=self._update_overlay_pos, size=self._update_overlay_pos)

    def _update_overlay_pos(self, *_):
        """Hält die Sperr-Maske exakt über dem Panel."""
        if self.overlay:
            self.overlay.pos = self.panel.pos
            self.overlay.size = self.panel.size

    def _on_unlock(self, *_):
        """Wird aufgerufen wenn Unlock-Button gedrückt wird."""
        self.unlock()
        if self.unlock_callback:
            self.unlock_callback()

    def unlock(self):
        """Entfernt die Sperr-Maske vom Screen."""
        if self.overlay:
            self.parent.remove_widget(self.overlay)
            self.overlay = None
            self.unlock_button = None

    def lock(self):
        """Re-aktiviert die Sperr-Maske (falls nötig für Auto-Lock)."""
        if not self.overlay:
            self.create()
