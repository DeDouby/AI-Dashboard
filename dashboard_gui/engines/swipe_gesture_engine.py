# dashboard_gui/engines/swipe_gesture_engine.py

from kivy.metrics import dp


class SwipeGestureEngine:

    def __init__(self, gsm):
        self.gsm = gsm
        self._swipe_threshold = dp(60)

        self._touch_start_x = None
        self._touch_active = False

    # ---------------------------------------------------------
    # PUBLIC API – Widgets rufen das hier
    # ---------------------------------------------------------
    def process_touch_down(self, touch):
        self._touch_start_x = touch.x
        self._touch_active = True

    def process_touch_move(self, touch):
        if not self._touch_active or self._touch_start_x is None:
            return

        dx = touch.x - self._touch_start_x

        if abs(dx) < self._swipe_threshold:
            return

        # Swipe erkannt
        direction = -1 if dx < 0 else 1
        self._handle_swipe(direction)

        # Lock nach einmaliger Ausführung
        self._touch_active = False
        self._touch_start_x = None

    def process_touch_up(self, touch):
        self._touch_active = False
        self._touch_start_x = None

    # ---------------------------------------------------------
    # CORE LOGIC
    # ---------------------------------------------------------
    def _handle_swipe(self, direction):
        """
        Direction:
        -1 = links → nächstes Gerät
        +1 = rechts → vorheriges Gerät
        """

        # 🔒 Safety Check: Darf überhaupt geswiped werden?
        if not self._can_swipe():
            return

        if direction < 0:
            self.gsm.next_device()
        else:
            self.gsm.previous_device()

    def _can_swipe(self):
        """
        Hier kommt deine Business-Logik rein.
        Z.B. kein Swipe wenn Fullscreen offen ist.
        """

        ui = self.gsm.ui_handler

        # Beispiel: Wenn fullscreen aktiv ist → Swipe blockieren
        if "fullscreen" in ui.screens:
            sm = getattr(self.gsm, "screen_manager", None)
            if sm and sm.current == "fullscreen":
                return False

        return True