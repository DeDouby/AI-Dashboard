# dashboard_gui/ui_screen_button_engine.py
class UIManager:
    def __init__(self, gsm):
        self.gsm = gsm  # Rückreferenz auf den Boss (GSM)
        self.broadcast_buttons = []# Alle Screen-Referenzen zentral hier
        self.active_inspector = None
        
        self.screens = {
            "dashboard": None, "fullscreen": None, "setup": None,
            "about": None, "settings": None, "vpd_scatter": None,
            "debug": None, "csv_viewer": None, "cam_viewer": None,
            "device_picker": None, "sensor_mixed_mode": None,
            "grow_controller": None, "plant_planner": None
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
# In dashboard_gui/ui_manager.py
    def _refresh_all_buttons(self):
        """Geht alle registrierten Screens durch und aktualisiert die Controls."""
        for name, scr in self.screens.items():
            if scr:
                # Prüfen, ob der Screen ein 'controls' Attribut hat (wie dein Dashboard)
                if hasattr(scr, "controls") and scr.controls:
                    scr.controls.refresh_state()
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

    def register_broadcast_button(self, btn):
        if btn not in self.broadcast_buttons:
            self.broadcast_buttons.append(btn)
            btn.refresh()

    def unregister_broadcast_button(self, btn):
        if btn in self.broadcast_buttons:
            self.broadcast_buttons.remove(btn)

    def refresh_broadcast_buttons(self):
        for btn in self.broadcast_buttons:
            btn.refresh()
    def get_device_label(self, dev_id):
        from dashboard_gui.global_state_manager import ACTIVE_CHANNEL_ENGINE
        return ACTIVE_CHANNEL_ENGINE.get_device_label(dev_id)

    def reset_all_screens(self):
        """Ruft auf JEDEM registrierten Screen die Reset-Logik auf."""
        for name, screen in self.screens.items():
            if hasattr(screen, 'reset_from_global'):
                print(f"[UIManager] Sende Reset an Screen: {name}")
                screen.reset_from_global()
   
    def open_signal_inspector(self, parent_header):
        # Falls schon einer offen ist -> sauber schließen
        if self.active_inspector:
            self.active_inspector.close()
        
        # Neuen erstellen
        from dashboard_gui.ui.common.signal_inspector import SignalInspector
        self.active_inspector = SignalInspector(parent_header=parent_header)
        
        # Dem Hauptfenster hinzufügen
        from kivy.core.window import Window
        Window.add_widget(self.active_inspector)
        
    def close_signal_inspector(self):
        if self.active_inspector:
            # Die close() Methode im Inspector entfernt ihn vom Parent
            self.active_inspector.close()
            self.active_inspector = None
