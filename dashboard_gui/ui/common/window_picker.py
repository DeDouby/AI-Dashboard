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
        w, h = dp(160), dp(200)
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
            ("menu.setup",       lambda: setattr(sm, "current", "setup")),
            ("menu.settings",    lambda: setattr(sm, "current", "settings")),
        ]

        if dev:
            entries += [
                ("menu.debug",  lambda: setattr(sm, "current", "debug")),
                ("menu.csv",    lambda: setattr(sm, "current", "csv_viewer")),
                ("menu.camera", lambda: setattr(sm, "current", "cam_viewer")),
            ]

        entries += [
            ("menu.devices", lambda: setattr(sm, "current", "device_picker")),
            ("menu.about",   lambda: setattr(sm, "current", "about")),
        ]

        # -----------------------------
        # 5) Buttons erzeugen (semi-transparent)
        # -----------------------------
        for label, cb in entries:
            b = Button(
                text=I18N.t(label),
                font_size=sp(18),
                background_color=(0.22, 0.25, 0.30, 0.55),
                color=(0.95, 0.95, 0.98, 1)
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
