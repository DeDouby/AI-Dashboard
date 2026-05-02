from kivy.uix.boxlayout import BoxLayout
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.global_state_manager import GLOBAL_STATE
from kivy.uix.label import Label
from kivy.app import App

class IconLabel(Label):
    def __init__(self, **kw):
        kw.setdefault("font_name", "FA")
        kw.setdefault("font_size", sp_scaled(22))
        kw.setdefault("halign", "center")
        kw.setdefault("valign", "middle")
        super().__init__(**kw)

class CirculationFanControl(BoxLayout):
    def __init__(self, parent_header=None, **kw):
        super().__init__(**kw)
        self.parent_header = parent_header
        self.orientation = "horizontal"
        self.size_hint = (None, 1)
        self.width = dp_scaled(45)
        self.latest_data = {}

        # Icon für den Lüfter (\uf72e)
        self.icon = IconLabel(text="\uf72e", font_size=sp_scaled(24))
        self.add_widget(self.icon)

    def set_rpm(self, rpm, data=None):
        if isinstance(data, dict):
            self.latest_data = data
            
        # 1. OFFLINE / PSEUDO-WERTE (z.B. -0.5, -256)
        if rpm is None or rpm < 0:
            self.icon.color = (0.4, 0.4, 0.4, 1)  # Grau
            return
    
        # 2. SAFE CAST
        try:
            val = int(rpm)
        except Exception:
            self.icon.color = (0.4, 0.4, 0.4, 1)  # Grau bei Fehler
            return
    
        # 3. FARBSTUFEN LOGIK (0 - 2000 RPM)
        if val <= 0:
            self.icon.color = (1, 0.2, 0.2, 1)    # Rot (Aus)
        elif val < 400:
            self.icon.color = (0, 0.7, 1, 1)      # Hellblau (Sanfte Brise)
        elif val < 800:
            self.icon.color = (0, 1, 0.5, 1)      # Türkis
        elif val < 1200:
            self.icon.color = (0, 1, 0, 1)        # Hellgrün (Optimal)
        elif val < 1600:
            self.icon.color = (1, 1, 0, 1)        # Gelb (Viel Umluft)
        else:
            self.icon.color = (1, 0.5, 0, 1)      # Orange (Maximum)
            
    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos): 
            return False
        
        # Lokaler Import verhindert Verzögerungen beim App-Start
        from dashboard_gui.overlays.circulation_fan_overlay import CirculationFanOverlay
        ui = GLOBAL_STATE.ui_handler
        
        # Sicherstellen, dass Overlays sich gegenseitig schließen
        if getattr(ui, "active_light_overlay", None):
            ui.active_light_overlay.close()

        if getattr(ui, "active_circulation_fan_overlay", None):
            ui.active_circulation_fan_overlay.close()
        else:
            overlay = CirculationFanOverlay(parent_header=self)
            ui.active_circulation_fan_overlay = overlay
            App.get_running_app().root.current_screen.add_widget(overlay)
            
        return True