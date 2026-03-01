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
from dashboard_gui.ui.i18n import I18N
from kivy.graphics import Rectangle, Color
from kivy.core.image import Image as CoreImage
import os
from kivy.uix.image import Image
from kivy.graphics import Color, Rectangle
from kivy.uix.togglebutton import ToggleButton

class SettingsMainPanel(BoxLayout):
    def __init__(self, on_save, on_cancel, **kw):
        super().__init__(**kw)
        self.orientation = "vertical"
        self.spacing = dp_scaled(10)
        self.padding = dp_scaled(12)

        self.on_save = on_save
        self.on_cancel = on_cancel
        self._lang_clicks = 0
        self._last_lang_ts = 0.0

        # --- Background mit Fallback ---
        bg_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "assets", "background_settings.png"
        )
        bg_path = os.path.abspath(bg_path)

        with self.canvas.before:
            
            
            if os.path.exists(bg_path):
                tex = CoreImage(bg_path).texture
                self.bg = Rectangle(texture=tex, pos=self.pos, size=self.size)
            else:
                Color(0.08,0.08,0.08,1)
                self.bg = Rectangle(pos=self.pos, size=self.size)
            
            self.bind(pos=self._update_bg, size=self._update_bg)

        # --- Rest deines bisherigen __init__ ---
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

        # ... der Rest bleibt unverändert ...

        # Helper: add slider
        def add_slider(label_text, key, min_v, max_v, step):
            row = BoxLayout(
                size_hint_y=None,
                height=dp_scaled(48),
                spacing=dp_scaled(10)
            )
            lbl = Label(text=I18N.t(label_text), size_hint=(0.35,1), font_size=sp_scaled(16))
            slider = Slider(min=min_v, max=max_v, step=step, value=float(self.cfg.get(key,0)), size_hint=(0.45,1))
            val = Label(text=str(self.cfg.get(key,0)), size_hint=(0.20,1), font_size=sp_scaled(16))
            slider.bind(value=lambda inst,v,lab=val: setattr(lab,"text",f"{v:.1f}"))
            self.inputs[key] = slider
            row.add_widget(lbl)
            row.add_widget(slider)
            row.add_widget(val)

            if not self.is_dev and key in ("refresh_interval","ui_refresh_interval","stale_timeout","tile_graph_window"):

                row.height = 0
                row.opacity = 0
                row.disabled = True

            container.add_widget(row)

        # --- Sliders ---
        # Min: 0.1, Max: 5.0, Schrittweite: 0.1
        add_slider("settings.refresh_interval","refresh_interval",0.1,5.0,0.1)
        add_slider("settings.ui_refresh_interval","ui_refresh_interval",0.1,5,0.1)
        add_slider("settings.stale_timeout","stale_timeout",5,60,1)
        add_slider("settings.tile_graph_window","tile_graph_window",30,5000,10)
        add_slider("settings.temp_offset","temperature_offset",-10,10,0.1)
        add_slider("settings.humidity_offset","humidity_offset",-20,20,1)
        add_slider("settings.leaf_offset","leaf_offset",-10,10,0.1)
        add_slider("LGS Send-Kanal", "lgs_mesh_channel_send", 0, 255, 1)
        add_slider("LGS Recv-Kanal", "lgs_mesh_channel_recv", 0, 255, 1)
        self._update_dev_visibility()

        # --- Temperature Unit Toggle ---
        toggle_row = BoxLayout(size_hint_y=None, height=dp_scaled(48), spacing=dp_scaled(10))
        toggle_row.add_widget(Label(text=I18N.t("settings.temperature_unit"), size_hint=(0.35,1), font_size=sp_scaled(16)))
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

        # --- Language Row ---
        lang_row = BoxLayout(size_hint_y=None, height=dp_scaled(48), spacing=dp_scaled(10))
        lang_row.add_widget(Label(text=I18N.t("settings.language"), size_hint=(0.35,1), font_size=sp_scaled(16)))

        self.lang_buttons = {}
        for code, label in [("en","EN"),("de","DE"),("es","ES")]:
            btn = Button(
                text=label,
                font_size=sp_scaled(16),
                background_color=(0.4,0.7,1,1) if self.cfg.get("language","en")==code else (0.3,0.3,0.3,1)
            )
            btn.bind(on_release=lambda inst, c=code: self._set_language(c))
            self.lang_buttons[code] = btn
            lang_row.add_widget(btn)

        container.add_widget(lang_row)
        # --- Theme Row ---
        theme_row = BoxLayout(size_hint_y=None, height=dp_scaled(48), spacing=dp_scaled(10))
        theme_row.add_widget(Label(
            text="Theme",
            size_hint=(0.35,1),
            font_size=sp_scaled(16)
        ))
        
        self.theme_buttons = {}
        current_theme = self.cfg.get("theme", "tiles")
        
        for theme_id, label in [
            ("tiles",  "Theme 1"),
            ("tiles2", "Theme 2"),
            ("tiles3", "Theme 3"),
        ]:
            btn = Button(
                text=label,
                font_size=sp_scaled(16),
                background_color=(0.4,0.7,1,1) if current_theme==theme_id else (0.3,0.3,0.3,1)
            )
            btn.bind(on_release=lambda inst, t=theme_id: self._set_theme(t))
            self.theme_buttons[theme_id] = btn
            theme_row.add_widget(btn)
        
        container.add_widget(theme_row)
        # --- Bottom Buttons ---
        btn_row = BoxLayout(size_hint_y=None, height=dp_scaled(36), spacing=dp_scaled(10))
        btn_reset = Button(text=I18N.t("settings.reset_defaults"), font_size=sp_scaled(16), background_color=(0.45,0.45,0.45,1))
        btn_reset.bind(on_release=lambda *_: self._reset_defaults())
        btn_save = Button(text=I18N.t("settings.save"), font_size=sp_scaled(18), background_color=(0.2,0.55,0.2,1))
        btn_save.bind(on_release=lambda *_: self.on_save(self._collect()))
        btn_cancel = Button(text=I18N.t("settings.cancel"), font_size=sp_scaled(18), background_color=(0.55,0.2,0.2,1))
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
       

        defaults = {
            "refresh_interval":0.5,
            "ui_refresh_interval":1.0,
            "stale_timeout":15.0,
            "tile_graph_window":300,
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


    def _update_bg(self, *_):
        self.bg.size = self.size
        self.bg.pos = self.pos
    def _collect(self):
        out = {k: v.value for k, v in self.inputs.items()}
        out["temperature_unit"] = self.temp_unit
        out["theme"] = config.get_theme()
        # Die Kanäle sind durch add_slider bereits in self.inputs[key].value
        return out

    def _update_dev_visibility(self):
        self.is_dev = config.is_developer_mode()
        for key in ("refresh_interval","ui_refresh_interval","stale_timeout","tile_graph_window"):

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

    def _set_theme(self, theme):
        import config
        cfg = config._init()
        cfg["theme"] = theme
        config.save(cfg)
    
        for t, btn in self.theme_buttons.items():
            btn.background_color = (0.4,0.7,1,1) if t==theme else (0.3,0.3,0.3,1)
    
        print(f"[SETTINGS] Theme switched to {theme}")

    def _set_language(self, code):
        import config
        import time
    
        now = time.time()
    
        # --- DEV TOGGLE nur bei DE ---
        if code == "de":
            if now - self._last_lang_ts > 2.5:
                self._lang_clicks = 0
            self._last_lang_ts = now
            self._lang_clicks += 1
    
            if self._lang_clicks == 7:
                new_state = not config.is_developer_mode()
                config.set_developer_mode(new_state)
                self._lang_clicks = 0
                self._update_dev_visibility()
                print("[DEV] Developer Mode", "activated" if new_state else "deactivated")
                return  # ⛔ wichtig: Sprache NICHT wechseln
        else:
            self._lang_clicks = 0  # Reset bei EN/ES
    
        # --- normale Sprachumschaltung ---
        cfg = config._init()
        cfg["language"] = code
        config.save(cfg)
    
        I18N.set_language(code)
    
        for c, btn in self.lang_buttons.items():
            btn.background_color = (0.4,0.7,1,1) if c==code else (0.3,0.3,0.3,1)
    
        print(f"[SETTINGS] Language switched to {code}")
