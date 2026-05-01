from kivy.uix.boxlayout import BoxLayout
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.global_state_manager import GLOBAL_STATE
from kivy.uix.label import Label
from kivy.app import App

# Falls du ein anderes Icon willst, hier ändern (z.B. \uf103 für Down-Arrow/Abluft)
class IconLabel(Label):
    def __init__(self, **kw):
        kw.setdefault("font_name", "FA")
        kw.setdefault("font_size", sp_scaled(22))
        kw.setdefault("halign", "center")
        kw.setdefault("valign", "middle")
        super().__init__(**kw)

class ExhaustFanControl(BoxLayout):
    def __init__(self, parent_header=None, **kw):
        super().__init__(**kw)
        self.parent_header = parent_header
        self.orientation = "horizontal"
        self.size_hint = (None, 1)
        self.width = dp_scaled(45)
        self.latest_data = {}
# NEU: Zugriff auf den GSM sicherstellen
        # Entweder vom parent_header übernehmen oder direkt vom GLOBAL_STATE
        if parent_header and hasattr(parent_header, 'gsm'):
            self.gsm = parent_header.gsm
        else:
            self.gsm = GLOBAL_STATE.gsm
        # \uf103 ist ein Pfeil nach unten (Abluft-Symbolik)
        self.icon = IconLabel(text="\uf863", font_size=sp_scaled(24))
        self.add_widget(self.icon)

    def set_rpm(self, rpm, data=None):
        if isinstance(data, dict):
            self.latest_data = data
        try:
            # 1. FEHLER/OFFLINE: Pseudo-Werte (z.B. -0.5, -255) abfangen
            if rpm is None or rpm < 0: 
                self.icon.color = (0.4, 0.4, 0.4, 1)  # Grau
                return
            
            val = int(rpm)

            # 2. FARBSTUFEN LOGIK (0 - 2000 RPM)
            if val <= 0:
                self.icon.color = (1, 0, 0, 1)        # Rot (Aus)
            elif val < 600:
                self.icon.color = (0, 0.7, 1, 1)      # Hellblau (Sehr niedrig)
            elif val < 800:
                self.icon.color = (0, 1, 0.5, 1)      # Türkis/Cyan (Niedrig)
            elif val < 1000:
                self.icon.color = (0, 1, 0, 1)        # Hellgrün (Optimal/Mittel)
            elif val < 1400:
                self.icon.color = (1, 0.8, 0, 1)      # Gelb/Orange (Hoch)
            else:
                self.icon.color = (1, 0.4, 0, 1)      # Dunkelorange/Rot (Maximum)
                
        except Exception:
            self.icon.color = (0.4, 0.4, 0.4, 1)      # Grau bei Crash

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos): return False
        ui = GLOBAL_STATE.ui_handler
        
        # Hier importieren wir nun das spezifische Exhaust-Overlay
        # Pfad ggf. anpassen, falls die Datei anders heißt
        from dashboard_gui.overlays.exhaust_fan_overlay import ExhaustFanOverlay
        
        if getattr(ui, "active_exhaust_fan_overlay", None):
            ui.active_exhaust_fan_overlay.close()
        else:
            overlay = ExhaustFanOverlay(parent_header=self)
            ui.active_exhaust_fan_overlay = overlay
            App.get_running_app().root.current_screen.add_widget(overlay)
        return True