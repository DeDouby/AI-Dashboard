# dashboard_gui/ui_manager.py

class UIManager:
    def __init__(self, gsm):
        self.gsm = gsm  # Rückreferenz auf den Boss (GSM)
        # Alle Screen-Referenzen zentral hier
        self.screens = {
            "dashboard": None, "fullscreen": None, "setup": None,
            "about": None, "settings": None, "vpd_scatter": None,
            "debug": None, "csv_viewer": None, "cam_viewer": None,
            "device_picker": None, "sensor_mixed_mode": None, "grow_rooms": None
        }

    def attach_screen(self, name, ref):
        """Registriert einen Screen im Manager."""
        if name in self.screens:
            self.screens[name] = ref

    def update_leds(self, led_state):
        """Pusht den LED-Status an ALLE registrierten Screens."""
        for name, scr in self.screens.items():
            if scr and hasattr(scr, 'header'):
                scr.header.set_led(led_state)
    # ---------------------------------------------------------
    # Button Sync
    # ---------------------------------------------------------
    def _refresh_all_buttons(self):
        if self.dashboard_ref and hasattr(self.dashboard_ref, "controls"):
            self.dashboard_ref.controls.refresh_state(self.running)
    
        if self.fullscreen_ref and hasattr(self.fullscreen_ref, "controls"):
            self.fullscreen_ref.controls.refresh_state(self.running)
    
        if self.vpd_scatter_ref and hasattr(self.vpd_scatter_ref, "controls"):
            self.vpd_scatter_ref.controls.refresh_state(self.running)
    def refresh_broadcast_buttons(self):
        """Aktualisiert die Broadcast-Buttons in allen Headern."""
        for name, scr in self.screens.items():
            if scr and hasattr(scr, 'header') and hasattr(scr.header, "btn_broadcast"):
                scr.header.btn_broadcast._refresh_state()
    def refresh_all_headers(self):
        for name, ref in self.ui_handler.screens.items():
            if ref and hasattr(ref, 'header'):
                if hasattr(ref.header, "btn_broadcast"):
                    ref.header.btn_broadcast._refresh_state()
    def update_active_screen(self, screen_manager, data_packet):
        """Sendet Daten nur an den aktuell sichtbaren Screen."""
        current_name = screen_manager.current
        current_scr = screen_manager.get_screen(current_name)
        
        if hasattr(current_scr, 'update_from_global'):
            current_scr.update_from_global(data_packet)