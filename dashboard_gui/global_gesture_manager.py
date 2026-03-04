# dashboard_gui/global_gesture_manager.py

class GlobalGestureManager:
    def __init__(self, gsm):
        self.gsm = gsm
        # Hier werden die Spezialisten geladen
        from dashboard_gui.gesture_engines.dashboard_swipe import DashboardSwipeEngine
        from dashboard_gui.gesture_engines.fullscreen_swipe import FullscreenSwipeEngine
        from dashboard_gui.gesture_engines.vpd_swipe import VPDSwipeEngine # NEU
        self.engines = {
            "dashboard": DashboardSwipeEngine(gsm),
            "fullscreen": FullscreenSwipeEngine(gsm),
            "vpd_scatter": VPDSwipeEngine(gsm) # NEU eingehängt
        }

    def handle_touch(self, screen_name, event_type, touch):
        """
        Zentraler Verteiler. 
        screen_name: Welcher Screen ruft an?
        event_type: "down", "move" oder "up"
        """
        engine = self.engines.get(screen_name)
        if not engine:
            return

        if event_type == "down":
            engine.process_touch_down(touch)
        elif event_type == "move":
            engine.process_touch_move(touch)
        elif event_type == "up":
            engine.process_touch_up(touch)