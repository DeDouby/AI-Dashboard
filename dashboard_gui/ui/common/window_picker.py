from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.metrics import dp, sp
from kivy.core.window import Window
from kivy.app import App
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.ui.i18n import I18N
import config

class WindowPicker(FloatLayout):
    def __init__(self, parent_header=None, **kwargs):
        super().__init__(**kwargs)
        self.parent_header = parent_header

        app = App.get_running_app()
        sm = app.root  # ScreenManager

        # -----------------------------
        # 1) Hintergrund Overlay
        # -----------------------------
        bg = Button(
            background_color=(0, 0, 0, 0.15),  # nur 15% Deckkraft → sehr transparent
            border=(0, 0, 0, 0)                # keine Kanten
        )
        bg.bind(on_release=lambda *_: self.close())
        self.add_widget(bg)

        # -----------------------------
        # 2) Panel für Buttons
        # -----------------------------
        w, h = dp(200), dp(280)
        self.panel = BoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            size=(w, h),
            spacing=dp(6),
            padding=[dp(4), dp(4), dp(4), dp(4)],
            pos=(Window.width - w - dp(10), Window.height - dp(50) - h)
        )
        self.add_widget(self.panel)

        # -----------------------------
        # 3) Dev Mode prüfen
        # -----------------------------
        try:
            dev = config.is_developer_mode()  # falls vorhanden
        except:
            dev = False  # fallback

        # -----------------------------
        # 4) Buttons & Navigation
        # -----------------------------
        entries = [
            ("menu.vpd_scatter", lambda: setattr(sm, "current", "vpd_scatter")),
            ("menu.sensor_mixed_mode", lambda: setattr(sm, "current", "sensor_mixed_mode")),
        ]

        if dev:
            entries += [
                ("menu.debug",  lambda: setattr(sm, "current", "debug")),
            ]

        entries += [
            ("menu.camera", lambda: setattr(sm, "current", "cam_viewer")),
            ("menu.grow_rooms", lambda: setattr(sm, "current", "grow_rooms")),
            ("menu.csv",    lambda: setattr(sm, "current", "csv_viewer")),  
            ("menu.devices", lambda: setattr(sm, "current", "device_picker")),
            ("menu.settings",    lambda: setattr(sm, "current", "settings")),
            ("menu.setup",       lambda: setattr(sm, "current", "setup")),
            ("menu.about",   lambda: setattr(sm, "current", "about")),
        ]

        # -----------------------------
        # 5) Buttons erzeugen (semi-transparent) mit FA-Icons
        # -----------------------------
        fa_map = {
            "menu.vpd_scatter":         "\uf201",   # fa-chart-scatter
            "menu.setup":               "\uf7d9",   # fa-cog
            "menu.settings":            "\uf013",   # fa-cog (kann gleich wie setup sein)
            "menu.debug":               "\uf1b9",   # fa-bug
            "menu.csv":                 "\uf1c3",   # fa-file-csv
            "menu.camera":              "\uf030",   # fa-camera
            "menu.devices":             "\uf2c7",   # fa-desktop / device
            "menu.sensor_mixed_mode":   "\uf1de", # ✅ sliders-h
            "menu.about":               "\uf05a",   # fa-info-circle
            "menu.grow_rooms":          "\uf015", # fa-home / grow room symbol
        }
        
        for label, cb in entries:
            icon = fa_map.get(label, "\uf128")  # default fa-question-circle
            b = Button(
                text=f"[font=FA]{icon}[/font]  {I18N.t(label)}",
                markup=True,
                font_size=sp(18),
            
                background_color=(0.22, 0.25, 0.30, 0.55),
                color=(0.95, 0.95, 0.98, 1),
            
                halign="left",
                valign="middle",
                padding=(dp(14), 0),
            
                text_size=(dp(200), None),   # FEST, kein Binding
            )
            b.bind(on_release=lambda _, f=cb: (f(), self.close()))
            self.panel.add_widget(b)

    # -----------------------------
    # 6) Overlay schließen
    # -----------------------------
    def close(self):
        if self.parent:
            self.parent.remove_widget(self)
            if self.parent_header:
                self.parent_header._menu_overlay = None
