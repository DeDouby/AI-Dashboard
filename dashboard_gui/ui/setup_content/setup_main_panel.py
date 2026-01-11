from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle
from kivy.uix.scrollview import ScrollView
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.ui.i18n import I18N

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
                 on_device_toggle=None,
                 on_adv=None, on_gatt=None, on_bridge=None,
                 on_restart_bridge=None, on_restart_adv=None, on_restart_gatt=None, 
                 **kw):
        super().__init__(orientation="vertical", spacing=15, **kw)

        self.on_device_toggle = on_device_toggle
        self.on_refresh = on_refresh
        self.on_save = on_save
        self.on_back = on_back
        self.on_restart_bridge = on_restart_bridge
        self.on_adv = on_adv
        self.on_gatt = on_gatt
        self.on_bridge = on_bridge

        # Hintergrund
        with self.canvas.before:
            Color(0.08, 0.08, 0.08, 1)
            self.bg = Rectangle()
        self.bind(size=self._update_bg, pos=self._update_bg)

        # --------------------------------------------------------
        # Decoder-Profile
        # --------------------------------------------------------
        BASE_DATA = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
        )
        BASE_DECODERS = os.path.join(BASE_DATA, "decoder_profiles")
        BASE_ADV  = os.path.join(BASE_DECODERS, "adv")
        BASE_GATT = os.path.join(BASE_DECODERS, "gatt")
        BASE_BRIDGE = os.path.join(BASE_DATA, "bridge_profiles")

        self.adv_profiles = ["---"] + sorted(f[:-5] for f in os.listdir(BASE_ADV) if f.endswith(".json")) if os.path.exists(BASE_ADV) else ["---"]
        self.gatt_profiles = ["---"] + sorted(f[:-5] for f in os.listdir(BASE_GATT) if f.endswith(".json")) if os.path.exists(BASE_GATT) else ["---"]
        self.bridge_profiles = ["---"] + sorted(f[:-5] for f in os.listdir(BASE_BRIDGE) if f.endswith(".json")) if os.path.exists(BASE_BRIDGE) else ["---"]

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
            text=I18N.t("menu.devices"),
            size_hint_x=0.25,
            halign="left",
            valign="middle",
            font_size=sp_scaled(14),
            color=(0.7, 0.7, 0.7, 1)
        ))
        legend.add_widget(Label(
            text=I18N.t("menu.adv") if "menu.adv" in I18N._translations[I18N._lang] else "ADV Decoder",
            size_hint_x=0.25,
            halign="center",
            valign="middle",
            font_size=sp_scaled(14),
            color=(0.7, 0.7, 0.7, 1)
        ))
        legend.add_widget(Label(
            text=I18N.t("menu.gatt") if "menu.gatt" in I18N._translations[I18N._lang] else "GATT Decoder",
            size_hint_x=0.25,
            halign="center",
            valign="middle",
            font_size=sp_scaled(14),
            color=(0.7, 0.7, 0.7, 1)
        ))
        legend.add_widget(Label(
            text=I18N.t("menu.bridge") if "menu.bridge" in I18N._translations[I18N._lang] else "Bridge Profile",
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
        
        # --- Refresh ---
        b = Button(
            text=f"[font=FA]\uf021[/font]  {I18N.t('control.refresh') if 'control.refresh' in I18N._translations[I18N._lang] else 'Refresh'}",
            markup=True,
            font_size=sp_scaled(18),
            background_color=(0.2, 0.2, 0.2, 1),
        )
        def _refresh_and_restart(*_):
            if self.on_refresh:
                self.on_refresh()
            if self.on_restart_bridge:
                self.on_restart_bridge()
        
        b.bind(on_release=_refresh_and_restart)
        btns.add_widget(b)
        
        # --- Save ---
        b = Button(
            text=f"[font=FA]\uf0c7[/font]  {I18N.t('settings.save')}",
            markup=True,
            font_size=sp_scaled(18),
            background_color=(0.2, 0.5, 0.2, 1),
        )
        b.bind(on_release=lambda *_: self.on_save())
        btns.add_widget(b)
        
        # --- Cancel ---
        b = Button(
            text=f"[font=FA]\uf060[/font]  {I18N.t('settings.cancel')}",
            markup=True,
            font_size=sp_scaled(18),
            background_color=(0.5, 0.2, 0.2, 1),
        )
        b.bind(on_release=lambda *_: self.on_back())
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
        row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(56),
            spacing=10,
            padding=[5, 5, 5, 5]
        )

        # linke Spalte: Name + MAC
        left = BoxLayout(orientation="vertical", size_hint_x=0.25, spacing=2)
        lbl_name = Label(text=name, size_hint_y=None, height=dp(26), halign="left", valign="middle", color=(0.9,0.9,0.9,1), font_size=dp(18))
        lbl_name.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))
        left.add_widget(lbl_name)

        lbl_mac = Label(text=mac, size_hint_y=None, height=dp(16), halign="left", valign="middle", color=(0.6,0.6,0.6,1), font_size=dp(11))
        lbl_mac.bind(size=lambda inst, _: setattr(inst, "text_size", inst.size))
        left.add_widget(lbl_mac)

        row.add_widget(left)

        # Non-Dev Mode Toggle
        from kivy.uix.togglebutton import ToggleButton
        toggle = ToggleButton(text=I18N.t('control.selected') if 'control.selected' in I18N._translations[I18N._lang] else "Selected", size_hint_x=0.25, state="down" if selected else "normal")
        if self.on_device_toggle:
            toggle.bind(state=lambda inst, val: self.on_device_toggle(mac, val=="down"))
        row.add_widget(toggle)

        # Dev Mode Spinner
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
