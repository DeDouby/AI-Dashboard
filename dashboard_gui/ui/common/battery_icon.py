from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.ui.common.icon_label import IconLabel
#######BATTERY
class BatteryIcon(BoxLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.orientation = "horizontal"
        self.spacing = dp_scaled(4)
        self.size_hint = (None, 1)
        self.width = dp_scaled(75) # Platz für Icon + "4.1V"

        self.icon = IconLabel(font_size=sp_scaled(22))
        self.text_label = Label(
            text="--V",
            font_size=sp_scaled(12),
            color=(0.8, 0.8, 0.8, 1),
            halign="left",
            valign="middle"
        )
        self.text_label.bind(size=self.text_label.setter('text_size'))

        self.add_widget(self.icon)
        self.add_widget(self.text_label)

    def set_voltage(self, voltage):
        if voltage is None or voltage < 0.1:
            self.icon.text = "\uf244" # Batterie leer Icon
            self.icon.color = (0.4, 0.4, 0.4, 1)
            self.text_label.text = "OFF"
            return

        self.text_label.text = f"{float(voltage):.2f}V"
        
        # Farblogik & Icons
        if voltage >= 3.9:
            self.icon.text = "\uf240" # Full
            self.icon.color = (0.3, 1, 0.3, 1) # Grün
        elif voltage >= 3.6:
            self.icon.text = "\uf242" # Half
            self.icon.color = (1, 0.8, 0.2, 1) # Gelb
        else:
            self.icon.text = "\uf243" # Low
            self.icon.color = (1, 0.2, 0.2, 1) # Rot
