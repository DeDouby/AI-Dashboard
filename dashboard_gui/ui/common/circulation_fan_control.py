from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.label import Label

from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.global_state_manager import GLOBAL_STATE

# Overlay import (kommt gleich)
from dashboard_gui.ui.common.fan_overlay import FanOverlay


class IconLabel(Label):
    def __init__(self, **kw):
        kw.setdefault("font_name", "FA")
        kw.setdefault("font_size", sp_scaled(22))
        kw.setdefault("halign", "center")
        kw.setdefault("valign", "middle")
        super().__init__(**kw)
        self.bind(size=lambda *_: self.texture_update())


class CirculationFanControl(BoxLayout):
    def __init__(self, parent_header=None, **kw):
        super().__init__(**kw)
        self.parent_header = parent_header
        self.orientation = "horizontal"
        self.size_hint = (None, 1)
        self.width = dp_scaled(45) # Schön kompakt

        # Nur das Icon - wir nutzen Markup für eventuelle Effekte.  
        self.icon = IconLabel(text="\uf72e", font_size=sp_scaled(24))
        self.add_widget(self.icon)

    def set_rpm(self, rpm):
        """ 
        Logik:
        - rpm ist None oder String-Fehler -> GRAU (Offline/Keine Info)
        - rpm ist 0 -> ROT (Lüfter steht/Blockiert)
        - rpm > 0 -> GRÜN (Läuft)
        """
        try:
            if rpm is None:
                self.icon.color = (0.4, 0.4, 0.4, 1) # Grau
                return

            val = int(rpm)
            
            if val > 0:
                self.icon.color = (0, 1, 0, 1)   # Giftgrün (Aktiv)
            else:
                self.icon.color = (1, 0, 0, 1)   # Hellrot (Stillstand)
                
        except (ValueError, TypeError):
            # Falls mal Müll ankommt (z.B. leeres JSON)
            self.icon.color = (0.4, 0.4, 0.4, 1) # Grau

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos): return False
        ui = GLOBAL_STATE.ui_handler
        if getattr(ui, "active_fan_overlay", None):
            ui.active_fan_overlay.close()
        else:
            overlay = FanOverlay(parent_header=self) # Wir übergeben uns selbst als Referenz
            ui.active_fan_overlay = overlay
            from kivy.app import App
            App.get_running_app().root.current_screen.add_widget(overlay)
        return True

    