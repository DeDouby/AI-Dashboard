# -*- coding: utf-8 -*-
"""
SettingsMainPanel – Scrollbare Version (Setup-Style)
Perfekt kompatibel mit SettingsScreen
© 2025 Dominik Rosenthal (Hackintosh1980)
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.button import Button
import time
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
import config

class SettingsMainPanel(BoxLayout):
    def __init__(self, on_save, on_cancel, **kw):
        super().__init__(**kw)
        self.orientation = "vertical"
        self.spacing = dp_scaled(10)
        self.padding = dp_scaled(12)

        self.on_save = on_save
        self.on_cancel = on_cancel
        self._reset_clicks = 0
        self._last_reset_ts = 0.0

        self.cfg = config._init()
        self.inputs = {}
        self.is_dev = config.is_developer_mode()

        # --- Scroll Area ---
        scroll = ScrollView(size_hint=(1,1))
        container = GridLayout(
            cols=1,
            spacing=dp_scaled(12),
            padding=[0, dp_scaled(6), 0, dp_scaled(6)],
            size_hint_y=None
        )
        container.bind(minimum_height=container.setter("height"))

        # Helper: add slider
        def add_slider(label_text, key, min_v, max_v, step):
            row = BoxLayout(
                size_hint_y=None,
                height=dp_scaled(48),
                spacing=dp_scaled(10)
            )
            lbl = Label(text=label_text, size_hint=(0.35,1), font_size=sp_scaled(16))
            slider = Slider(min=min_v, max=max_v, step=step, value=float(self.cfg.get(key,0)), size_hint=(0.45,1))
            val = Label(text=str(self.cfg.get(key,0)), size_hint=(0.20,1), font_size=sp_scaled(16))
            slider.bind(value=lambda inst,v,lab=val: setattr(lab,"text",f"{v:.1f}"))
            self.inputs[key] = slider
            row.add_widget(lbl)
            row.add_widget(slider)
            row.add_widget(val)

            if not self.is_dev and key in ("refresh_interval","ui_refresh_interval","stale_timeout"):
                row.height = 0
                row.opacity = 0
                row.disabled = True

            container.add_widget(row)

        # --- Sliders ---
        add_slider("Refresh Interval","refresh_interval",0.5,10,0.5)
        add_slider("UI Refresh","ui_refresh_interval",0.1,5,0.1)
        add_slider("Stale Timeout","stale_timeout",5,60,1)
        add_slider("Temp Offset","temperature_offset",-10,10,0.1)
        add_slider("Humidity Offset","humidity_offset",-20,20,1)
        add_slider("Leaf Offset","leaf_offset",-10,10,0.1)

        self._update_dev_visibility()

        # --- Temperature Unit Toggle ---
        toggle_row = BoxLayout(size_hint_y=None, height=dp_scaled(48), spacing=dp_scaled(10))
        toggle_row.add_widget(Label(text="Temperature Unit", size_hint=(0.35,1), font_size=sp_scaled(16)))
        self.temp_unit = self.cfg.get("temperature_unit","C")
        self.btn_C = Button(text="°C", font_size=sp_scaled(18), background_color=(0.4,0.7,1,1) if self.temp_unit=="C" else (0.3,0.3,0.3,1))
        self.btn_F = Button(text="°F", font_size=sp_scaled(18), background_color=(0.4,0.7,1,1) if self.temp_unit=="F" else (0.3,0.3,0.3,1))
        self.btn_C.bind(on_release=lambda *_: self._set_unit("C"))
        self.btn_F.bind(on_release=lambda *_: self._set_unit("F"))
        toggle_row.add_widget(self.btn_C)
        toggle_row.add_widget(self.btn_F)
        container.add_widget(toggle_row)

        scroll.add_widget(container)
        self.add_widget(scroll)
        # nach Unit Toggle hinzufügen, also unter self.temp_unit Row
        lang_row = BoxLayout(
            size_hint_y=None,
            height=dp_scaled(48),
            spacing=dp_scaled(10)
        )
        
        lang_row.add_widget(Label(
            text="Language",
            size_hint=(0.35, 1),
            font_size=sp_scaled(16)
        ))
        
        self.lang_buttons = {}
        for code, label in [("en", "EN"), ("de", "DE"), ("es", "ES")]:
            btn = Button(
                text=label,
                font_size=sp_scaled(16),
                background_color=(0.4, 0.7, 1, 1) if config._init().get("language", "en") == code else (0.3,0.3,0.3,1)
            )
            btn.bind(on_release=lambda inst, c=code: self._set_language(c))
            self.lang_buttons[code] = btn
            lang_row.add_widget(btn)
        
        container.add_widget(lang_row)
        # --- Bottom Buttons ---
        btn_row = BoxLayout(size_hint_y=None, height=dp_scaled(36), spacing=dp_scaled(10))
        btn_reset = Button(text="Reset Defaults", font_size=sp_scaled(16), background_color=(0.45,0.45,0.45,1))
        btn_reset.bind(on_release=lambda *_: self._reset_defaults())
        btn_save = Button(text="Save", font_size=sp_scaled(18), background_color=(0.2,0.55,0.2,1))
        btn_save.bind(on_release=lambda *_: self.on_save(self._collect()))
        btn_cancel = Button(text="Cancel", font_size=sp_scaled(18), background_color=(0.55,0.2,0.2,1))
        btn_cancel.bind(on_release=lambda *_: self.on_cancel())
        btn_row.add_widget(btn_reset)
        btn_row.add_widget(btn_save)
        btn_row.add_widget(btn_cancel)
        self.add_widget(btn_row)

    # -----------------------------
    # Helper Methods
    # -----------------------------
    def _set_unit(self, u):
        self.temp_unit = u
        self.btn_C.background_color = (0.4,0.7,1,1) if u=="C" else (0.3,0.3,0.3,1)
        self.btn_F.background_color = (0.4,0.7,1,1) if u=="F" else (0.3,0.3,0.3,1)

    def _reset_defaults(self):
        now = time.time()
        if now - self._last_reset_ts > 2.5:
            self._reset_clicks = 0
        self._last_reset_ts = now
        self._reset_clicks += 1

        defaults = {
            "refresh_interval":2.0,
            "ui_refresh_interval":1.0,
            "stale_timeout":15.0,
            "temperature_offset":0.0,
            "humidity_offset":0.0,
            "leaf_offset":0.0,
            "temperature_unit":"C"
        }

        for k,v in defaults.items():
            if k=="temperature_unit":
                self._set_unit(v)
            elif k in self.inputs:
                self.inputs[k].value = v

        # 7x Reset → Toggle DEV Mode
        if self._reset_clicks==7:
            new_state = not config.is_developer_mode()
            config.set_developer_mode(new_state)
            self._reset_clicks = 0
            self._update_dev_visibility()
            print("[DEV] Developer Mode", "activated" if new_state else "deactivated")

    def _collect(self):
        out = {k:v.value for k,v in self.inputs.items()}
        out["temperature_unit"] = self.temp_unit
        return out

    def _update_dev_visibility(self):
        self.is_dev = config.is_developer_mode()
        for key in ("refresh_interval","ui_refresh_interval","stale_timeout"):
            slider = self.inputs.get(key)
            if not slider:
                continue
            row = slider.parent
            if self.is_dev:
                row.disabled = False
                row.opacity = 1
                row.height = dp_scaled(48)
            else:
                row.disabled = True
                row.opacity = 0
                row.height = 0
    def _set_language(self, code):
        import config
        from dashboard_gui.ui.i18n import I18N
        
        # in Config speichern
        cfg = config._init()
        cfg["language"] = code
        config.save(cfg)
        
        # I18N setzen
        I18N.set_language(code)
        
        # Buttons aktualisieren
        for c, btn in self.lang_buttons.items():
            btn.background_color = (0.4, 0.7, 1, 1) if c == code else (0.3,0.3,0.3,1)
        
        print(f"[SETTINGS] Language switched to {code}")