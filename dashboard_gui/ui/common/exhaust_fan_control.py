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

        # \uf103 ist ein Pfeil nach unten (Abluft-Symbolik)
        self.icon = IconLabel(text="\uf863", font_size=sp_scaled(24))
        self.add_widget(self.icon)

    def set_rpm(self, rpm):
        try:
            if rpm is None or rpm < 0: # Berücksichtigung deiner Pseudo-Werte
                self.icon.color = (0.4, 0.4, 0.4, 1)
                return
            val = int(rpm)
            self.icon.color = (0, 0.7, 1, 1) if val > 0 else (1, 0, 0, 1)
        except:
            self.icon.color = (0.4, 0.4, 0.4, 1)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos): return False
        ui = GLOBAL_STATE.ui_handler
        
        # Hier importieren wir nun das spezifische Exhaust-Overlay
        # Pfad ggf. anpassen, falls die Datei anders heißt
        from dashboard_gui.ui.common.exhaust_fan_overlay import ExhaustFanOverlay
        
        if getattr(ui, "active_exhaust_overlay", None):
            ui.active_exhaust_overlay.close()
        else:
            overlay = ExhaustFanOverlay(parent_header=self)
            ui.active_exhaust_overlay = overlay
            App.get_running_app().root.current_screen.add_widget(overlay)
        return True