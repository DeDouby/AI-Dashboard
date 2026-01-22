# device_picker_menu.py
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
import config

class DevicePickerMenu(FloatLayout):
    def __init__(self, parent_header, device_list, on_select_device, **kw):
        super().__init__(**kw)
        self.parent_header = parent_header

        from dashboard_gui.global_state_manager import GLOBAL_STATE
        self._current_idx = GLOBAL_STATE.active_index

        # -----------------------------
        # 1) Hintergrund Overlay (leicht abdunkeln)
        # -----------------------------
        bg = Button(
            background_color=(0, 0, 0, 0.15),  # 15% Deckkraft
            border=(0, 0, 0, 0)
        )
        bg.bind(on_release=lambda *_: self.close())
        self.add_widget(bg)

        # -----------------------------
        # 2) Panel für Buttons
        # -----------------------------
        num_buttons = len(device_list) + 2  # + ADV + GATT
        self.panel_width = dp_scaled(200)
        panel_height = dp_scaled(120 * len(device_list) + 20)

        # Absolute Window-Position des Buttons
        btn_x, btn_y = parent_header.lbl_dev.to_window(*parent_header.lbl_dev.pos)

        # Panel direkt **unterhalb des Buttons** platzieren
        panel_x = btn_x
        panel_y = btn_y - panel_height + parent_header.lbl_dev.height

        # Sicherstellen, dass Panel nicht unter Bildschirm fällt
        panel_y = max(panel_y, 0)

        self.panel = BoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            size=(self.panel_width, panel_height),
            spacing=dp_scaled(8),
            padding=[dp_scaled(6)]*4,
            pos=(panel_x, panel_y)
        )
        self.add_widget(self.panel)


        # -----------------------------
        # 3) Devices aus Config
        # -----------------------------
        cfg = config._init()
        devices_cfg = cfg.get("devices", {})

        for idx, mac in enumerate(device_list):
            name = devices_cfg.get(mac, {}).get("name")
            label = name if name else mac
        
            b = Button(
                text=f"[font=FA]\uf2c7[/font]  {label}",
                font_size=sp_scaled(20),
                markup=True,
                size_hint_y=None,
                height=dp_scaled(50),
            
                background_color=(0.22, 0.25, 0.30, 0.55),
                color=(0.95, 0.95, 0.98, 1),
            
                halign="left",
                valign="middle",
                padding=(dp_scaled(14), 0),
                text_size=(self.panel_width, None),
            )
        
            b.bind(on_release=lambda _, i=idx: (
                on_select_device(i),
                setattr(self, "_current_idx", i),
                self.close()
            ))
        
            self.panel.add_widget(b)
        # -----------------------------
        # 4) Separator
        # -----------------------------
        sep = Label(
            text="-- CHANNEL --",
            font_size=sp_scaled(16),
            color=(0.8, 0.8, 0.8, 1),
            size_hint_y=None,
            height=dp_scaled(30)
        )
        self.panel.add_widget(sep)

        # -----------------------------
        # 5) Channel Buttons (ADV / GATT)
        # -----------------------------
        self._add_channel_buttons(device_list, cfg)

    # -----------------------------
    # Channel Buttons separat
    # -----------------------------
    def _add_channel_buttons(self, device_list, cfg):
        from dashboard_gui.global_state_manager import GLOBAL_STATE
    
        # -----------------------------
        # ADV Button
        # -----------------------------
        b_adv = Button(
            text=f"[font=FA]\uf1eb[/font]  ADV channel",
            font_size=sp_scaled(20),
            markup=True,
            size_hint_y=None,
            height=dp_scaled(50),
        
            background_color=(0.20, 0.30, 0.25, 0.55),
            color=(0.95, 0.95, 0.98, 1),
        
            halign="left",
            valign="middle",
            padding=(dp_scaled(14), 0),
            text_size=(self.panel_width, None),
        )
        def activate_adv():
            GLOBAL_STATE.set_active_channel("adv")
            self.close()
        
        b_adv.bind(on_release=lambda *_: activate_adv())
        self.panel.add_widget(b_adv)
    
        # -----------------------------
        # GATT Button
        # -----------------------------
        b_gatt = Button(
            text=f"[font=FA]\uf0c1[/font]  GATT channel",
            font_size=sp_scaled(20),
            markup=True,
            size_hint_y=None,
            height=dp_scaled(50),
        
            background_color=(0.25, 0.20, 0.30, 0.55),
            color=(0.95, 0.95, 0.98, 1),
        
            halign="left",
            valign="middle",
            padding=(dp_scaled(14), 0),
            text_size=(self.panel_width, None),
        )
        def activate_gatt():
            idx = self._current_idx if self._current_idx is not None else 0
            device_id = device_list[idx]
            GLOBAL_STATE.set_active_channel("gatt")
            self.close()
    
        b_gatt.bind(on_release=lambda *_: activate_gatt())
        self.panel.add_widget(b_gatt)

    # -----------------------------
    # Menü schließen
    # -----------------------------
    def close(self):
        if self.parent:
            self.parent.remove_widget(self)
            if self.parent_header:
                self.parent_header._device_menu = None
