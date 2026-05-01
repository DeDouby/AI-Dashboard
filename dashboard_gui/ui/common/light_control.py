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
        # 1. NICHT VORHANDEN / OFFLINE
        if brightness is None:
            self.icon.text = "\uf0eb"
            self.icon.color = (0.3, 0.3, 0.3, 1)  # Grau
            return
    
        # 2. SAFE CAST
        try:
            val = int(brightness)
        except:
            self.icon.text = "\uf0eb"
            self.icon.color = (0.3, 0.3, 0.3, 1)  # Grau bei Müll
            return
    
        # 3. SEMANTIK
        if val > 0:
            # AN
            self.icon.text = "\uf0eb"
            self.icon.color = (1, 1, 0, 1)   # Grün
        else:
            # AUS (explizit!)
            self.icon.text = "\uf0eb"
            self.icon.color = (1, 0.2, 0.2, 1)   # Rot
            
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