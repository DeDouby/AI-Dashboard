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
class LightControl(BoxLayout):
    def __init__(self, parent_header=None, **kw):
        super().__init__(**kw)
        self.parent_header = parent_header
        self.orientation = "horizontal"
        self.size_hint = (None, 1)
        self.width = dp_scaled(45)
        self.latest_data = {}

        # Icons (FontAwesome Hex-Codes):
        # \uf0eb -> bulb (solid/filled)
        # \ue4e3 -> lightbulb-slash (oder alternativ \uf0eb mit weniger Opacity)
        self.icon_on = "\uf0eb"  
        self.icon_off = "\uf0eb" # Wir nutzen das gleiche Icon, ändern aber das Feeling

        self.icon = IconLabel(text=self.icon_on, font_size=sp_scaled(24))
        self.add_widget(self.icon)

    def set_brightness(self, brightness, data=None):
        if isinstance(data, dict):
            self.latest_data = data

        # 1. OFFLINE / SENSOR-FEHLER (Pseudo-Werte < 0)
        # Grau durchscheinend (Alpha 0.5) signalisiert Verbindungsabbruch
        if brightness is None or brightness < 0:
            self.icon.color = (0.5, 0.5, 0.5, 0.5) 
            return
    
        # 2. SAFE CAST
        try:
            val = int(brightness)
        except Exception:
            self.icon.color = (0.5, 0.5, 0.5, 0.5)
            return
    
        # 3. LICHT-STUFEN (Gelbstufen je nach Prozentwert)
        if val <= 0:
            # AUS: Ein eindeutiges, sattes Anthrazit-Grau
            self.icon.color = (0.2, 0.2, 0.2, 1) 
        elif val < 20:
            # Ganz schwaches Glimmen (Dunkel-Gold)
            self.icon.color = (0.6, 0.5, 0, 1)
        elif val < 50:
            # Gedimmtes Licht (Standard-Gelb)
            self.icon.color = (0.8, 0.8, 0, 1)
        elif val < 80:
            # Hell (Leuchtendes Gelb)
            self.icon.color = (1, 1, 0, 1)
        else:
            # VOLLGAS (Strahlenweißes Gelb)
            # Hier mischen wir etwas Weiß bei (1, 1, 0.6), damit es "leuchtet"
            self.icon.color = (1, 1, 0.6, 1)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos): return False
        
        from dashboard_gui.overlays.light_overlay import LightOverlay
        ui = GLOBAL_STATE.ui_handler
        
        # Sicherstellen, dass wir nicht beide Overlays gleichzeitig offen haben
        if getattr(ui, "active_fan_overlay", None):
            ui.active_fan_overlay.close()

        if getattr(ui, "active_light_overlay", None):
            ui.active_light_overlay.close()
        else:
            overlay = LightOverlay(parent_header=self)
            ui.active_light_overlay = overlay
            App.get_running_app().root.current_screen.add_widget(overlay)
        return True