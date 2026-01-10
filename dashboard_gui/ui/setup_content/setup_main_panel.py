# setup_main_panel.py – Session46 FINAL

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle
from kivy.uix.scrollview import ScrollView
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled

import os

# ------------------------------------------------------------
# Profile-Liste aus data/decoder_profiles laden
# ------------------------------------------------------------
def list_profiles():
    base = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "decoder_profiles")
    names = []
    if os.path.exists(base):
        for f in os.listdir(base):
            if f.endswith(".json"):
                names.append(f.replace(".json", ""))
    return sorted(names)


# ------------------------------------------------------------
# Hauptklasse
# ------------------------------------------------------------
class SetupMainPanel(BoxLayout):
    def __init__(self, on_refresh, on_save, on_back, on_profile_change,
                 on_device_toggle=None,  # <-- neu
                 on_adv=None, on_gatt=None, on_bridge=None,
                 on_restart_bridge=None, on_restart_adv=None, on_restart_gatt=None, 
                 **kw):
        super().__init__(orientation="vertical", spacing=15, **kw)

        self.on_device_toggle = on_device_toggle  # <-- speichern

        self.on_refresh = on_refresh
        self.on_save = on_save
        self.on_back = on_back
        self.on_restart_bridge = on_restart_bridge
        self.on_adv = on_adv
        self.on_gatt = on_gatt
        self.on_bridge = on_bridge

        # Callbacks
        self.on_bridge = on_bridge

        # Hintergrund
        with self.canvas.before:
            Color(0.08, 0.08, 0.08, 1)
            self.bg = Rectangle()

        self.bind(size=self._update_bg, pos=self._update_bg)

        # --------------------------------------------------------
        # Decoder-Profile – sauber getrennt nach ADV / GATT
        # --------------------------------------------------------
        
        BASE_DATA = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..", "..", "..",
                "data"
            )
        )
        
        BASE_DECODERS = os.path.join(BASE_DATA, "decoder_profiles")
        BASE_ADV  = os.path.join(BASE_DECODERS, "adv")
        BASE_GATT = os.path.join(BASE_DECODERS, "gatt")
        
        # --------------------------------------------------------
        # ADV Decoder
        # --------------------------------------------------------
        if os.path.exists(BASE_ADV):
            self.adv_profiles = ["---"] + sorted(
                f[:-5] for f in os.listdir(BASE_ADV) if f.endswith(".json")
            )
        else:
            self.adv_profiles = ["---"]
        
        # --------------------------------------------------------
        # GATT Decoder
        # --------------------------------------------------------
        if os.path.exists(BASE_GATT):
            self.gatt_profiles = ["---"] + sorted(
                f[:-5] for f in os.listdir(BASE_GATT) if f.endswith(".json")
            )
        else:
            self.gatt_profiles = ["---"]
        
        # --------------------------------------------------------
        # BRIDGE-Profile (aus data/bridge_profiles)
        # --------------------------------------------------------
        
        BASE_BRIDGE = os.path.join(BASE_DATA, "bridge_profiles")
        
        if os.path.exists(BASE_BRIDGE):
            self.bridge_profiles = ["---"] + sorted(
                f[:-5] for f in os.listdir(BASE_BRIDGE) if f.endswith(".json")
            )
        else:
            self.bridge_profiles = ["---"]

        # --------------------------------------------------------
        # Spalten-Legende
        # --------------------------------------------------------
        legend = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(28),
            spacing=10,
            padding=[5, 0, 5, 0]
        )
        
        legend.add_widget(Label(
            text="Device List",
            size_hint_x=0.25,
            halign="left",
            valign="middle",
            font_size=sp_scaled(14),
            color=(0.7, 0.7, 0.7, 1)
        ))
        
        legend.add_widget(Label(
            text="ADV Decoder",
            size_hint_x=0.25,
            halign="center",
            valign="middle",
            font_size=sp_scaled(14),
            color=(0.7, 0.7, 0.7, 1)
        ))
        
        legend.add_widget(Label(
            text="GATT Decoder",
            size_hint_x=0.25,
            halign="center",
            valign="middle",
            font_size=sp_scaled(14),
            color=(0.7, 0.7, 0.7, 1)
        ))
        
        legend.add_widget(Label(
            text="Bridge Profile",
            size_hint_x=0.25,
            halign="center",
            valign="middle",
            font_size=sp_scaled(14),
            color=(0.7, 0.7, 0.7, 1)
        ))
        
        self.add_widget(legend)

        # --------------------------------------------------------
        # Scrollable list
        # --------------------------------------------------------
        scroll = ScrollView(size_hint=(1, 1))
        self.device_box = BoxLayout(
            orientation="vertical",
            spacing=8,
            padding=[5, 5, 5, 5],
            size_hint_y=None
        )
        self.device_box.bind(minimum_height=self.device_box.setter("height"))
        scroll.add_widget(self.device_box)
        self.add_widget(scroll)

        # --------------------------------------------------------
        # Buttons unten
        # --------------------------------------------------------
        btns = BoxLayout(size_hint_y=None, height=dp(36), spacing=15)

        b = Button(
            text="[font=FA]\uf021[/font]  Refresh",
            markup=True,
            font_size=sp_scaled(18),
            background_normal="",
            background_down="",
            background_color=(0.2, 0.2, 0.2, 1),
        )
        b.bind(on_release=lambda *_: self.on_refresh())
        btns.add_widget(b)
        
        b = Button(
            text="[font=FA]\uf0c7[/font]  Save",
            markup=True,
            font_size=sp_scaled(18),
            background_normal="",
            background_down="",
            background_color=(0.2, 0.5, 0.2, 1),
        )
        b.bind(on_release=lambda *_: self.on_save())
        btns.add_widget(b)

        b = Button(
            text="[font=FA]\uf060[/font]  Back",
            markup=True,
            font_size=sp_scaled(18),
            background_normal="",
            background_down="",
            background_color=(0.5, 0.2, 0.2, 1),
        )
        b.bind(on_release=lambda *_: self.on_back())
        btns.add_widget(b)

        b = Button(
            text="[font=FA]\uf021[/font]  Restart Core",
            markup=True,
            font_size=sp_scaled(20),
            background_normal="",
            background_down="",
            background_color=(0.3, 0.3, 0.6, 1),
            padding=[dp_scaled(10), dp_scaled(10)],
        )
        
        if self.on_restart_bridge:
            b.bind(on_release=lambda *_: self.on_restart_bridge())
        else:
            b.disabled = True
        
        btns.add_widget(b)

        self.add_widget(btns)

    # --------------------------------------------------------
    def _update_bg(self, *_):
        self.bg.size = self.size
        self.bg.pos = self.pos

    # --------------------------------------------------------
    def clear_devices(self):
        self.device_box.clear_widgets()

    # --------------------------------------------------------
    # Gerät hinzufügen (ADV + GATT + BRIDGE)
    # --------------------------------------------------------
    def add_device(self, name, mac, adv=None, gatt=None, bridge=None, selected=True):
        """
        Fügt ein Gerät hinzu.
        - Non-Dev Mode: nur Name + ToggleButton
        - Dev Mode: Spinner für adv/gatt/bridge
        """
    
        row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(56),
            spacing=10,
            padding=[5, 5, 5, 5]
        )
    
        # linke Spalte: Name + MAC
        left = BoxLayout(orientation="vertical", size_hint_x=0.25, spacing=2)
    
        lbl_name = Label(
            text=name,
            size_hint_y=None,
            height=dp(26),
            halign="left",
            valign="middle",
            color=(0.9, 0.9, 0.9, 1),
            font_size=dp(18)
        )
        lbl_name.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))
        left.add_widget(lbl_name)
    
        lbl_mac = Label(
            text=mac,
            size_hint_y=None,
            height=dp(16),
            halign="left",
            valign="middle",
            color=(0.6, 0.6, 0.6, 1),
            font_size=dp(11)
        )
        lbl_mac.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))
        left.add_widget(lbl_mac)
    
        row.add_widget(left)
    
        # ✅ Non-Dev Mode: ToggleButton für Auswahl
        from kivy.uix.togglebutton import ToggleButton
        
        toggle = ToggleButton(
            text="Selected",
            size_hint_x=0.25,
            state="down" if selected else "normal"
        )
        
        # Prüfen, ob Callback existiert
        if self.on_device_toggle:
            toggle.bind(state=lambda inst, val: self.on_device_toggle(mac, val=="down"))
        
        row.add_widget(toggle)
    
        # Dev Mode: nur wenn adv/gatt/bridge übergeben sind
        if adv is not None and gatt is not None and bridge is not None:
            sp_adv = Spinner(text=adv or "---", values=self.adv_profiles, size_hint_x=0.25)
            sp_adv.bind(text=lambda _, val: self.on_adv(mac, val))
            row.add_widget(sp_adv)
    
            sp_gatt = Spinner(text=gatt or "---", values=self.gatt_profiles, size_hint_x=0.25)
            sp_gatt.bind(text=lambda _, val: self.on_gatt(mac, val))
            row.add_widget(sp_gatt)
    
            sp_bridge = Spinner(text=bridge or "---", values=self.bridge_profiles, size_hint_x=0.25)
            sp_bridge.bind(text=lambda _, val: self.on_bridge(mac, val))
            row.add_widget(sp_bridge)
    
        self.device_box.add_widget(row)