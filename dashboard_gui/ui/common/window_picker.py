from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.app import App
from kivy.uix.scrollview import ScrollView
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.ui.i18n import I18N
from dashboard_gui.global_state_manager import GLOBAL_STATE
import config


class WindowPicker(FloatLayout):
    def __init__(self, parent_header=None, **kwargs):
        super().__init__(**kwargs)
        self.parent_header = parent_header

        app = App.get_running_app()
        sm = app.root

        # --------------------------------------------------
        # Hintergrund Overlay
        # --------------------------------------------------
        bg = Button(
            background_color=(0, 0, 0, 0.15),
            border=(0, 0, 0, 0)
        )
        bg.bind(on_release=lambda *_: self.close())
        self.add_widget(bg)

        # --------------------------------------------------
        # Responsive Menügröße
        # --------------------------------------------------
        w = min(dp_scaled(300), Window.width * 0.45)
        h = min(dp_scaled(1200), Window.height * 0.85)

        # --------------------------------------------------
        # ScrollView Panel
        # --------------------------------------------------
        self.panel = ScrollView(
            size_hint=(None, None),
            size=(w, h),
            pos=(
                Window.width - w - dp_scaled(10),
                Window.height - dp_scaled(55) - h
            ),
            do_scroll_x=False,
            do_scroll_y=True,
            bar_width=dp_scaled(4),
            scroll_type=["bars", "content"]
        )
        self.add_widget(self.panel)

        # --------------------------------------------------
        # Inhalt
        # --------------------------------------------------
        self.panel_content = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp_scaled(6),
            padding=[
                dp_scaled(4),
                dp_scaled(4),
                dp_scaled(4),
                dp_scaled(4)
            ]
        )

        self.panel_content.bind(
            minimum_height=self.panel_content.setter("height")
        )

        self.panel.add_widget(self.panel_content)

        # --------------------------------------------------
        # Dev Mode
        # --------------------------------------------------
        try:
            dev = config.is_developer_mode()
        except Exception:
            dev = False

# --------------------------------------------------
        # Navigationseinträge
        # --------------------------------------------------
        # Wir nutzen überall den ui_handler.goto(), damit der 
        # navigation_stack korrekt mit den Screens befüllt wird.
        
        entries = [
            ("menu.vpd_scatter", 
             lambda: GLOBAL_STATE.ui_handler.goto("vpd_scatter")),
            
            ("menu.sensor_mixed_mode", 
             lambda: GLOBAL_STATE.ui_handler.goto("sensor_mixed_mode")),
        ]

        if dev:
            entries += [
                ("menu.debug", 
                 lambda: GLOBAL_STATE.ui_handler.goto("debug")),
            ]

        entries += [
            ("menu.camera", 
             lambda: GLOBAL_STATE.ui_handler.goto("cam_viewer")),
        
            ("menu.grow_controller", 
             lambda: GLOBAL_STATE.ui_handler.goto("grow_controller")),
        
            ("menu.grow_overview", 
             lambda: GLOBAL_STATE.ui_handler.goto("grow_overview")),
        
            ("menu.plant_planner", 
             lambda: GLOBAL_STATE.ui_handler.goto("plant_planner")),
        
            ("menu.csv", 
             lambda: GLOBAL_STATE.ui_handler.goto("csv_viewer")),
        
            ("menu.devices", 
             lambda: GLOBAL_STATE.ui_handler.goto("device_picker")),
        
            ("menu.settings", 
             lambda: GLOBAL_STATE.ui_handler.goto("settings")),
        
            ("menu.setup", 
             lambda: GLOBAL_STATE.ui_handler.goto("setup")),
        
            ("menu.about", 
             lambda: GLOBAL_STATE.ui_handler.goto("about")),
        ]

        # --------------------------------------------------
        # Icons
        # --------------------------------------------------
        fa_map = {
            "menu.vpd_scatter": "\uf201",
            "menu.setup": "\uf7d9",
            "menu.settings": "\uf013",
            "menu.debug": "\uf1b9",
            "menu.csv": "\uf1c3",
            "menu.camera": "\uf030",
            "menu.devices": "\uf2c7",
            "menu.sensor_mixed_mode": "\uf1de",
            "menu.about": "\uf05a",
            "menu.grow_controller": "\uf015",
            "menu.plant_planner": "\uf073",
            "menu.grow_overview": "\uf1bb",
        }
        # --------------------------------------------------
        # Buttons erzeugen
        # --------------------------------------------------
        for label, cb in entries:
            icon = fa_map.get(label, "\uf128")

            b = Button(
                text=f"[font=FA]{icon}[/font]  {I18N.t(label)}",
                markup=True,
                font_size=sp_scaled(23),
                background_color=(0.22, 0.25, 0.30, 0.55),
                color=(0.95, 0.95, 0.98, 1),
                halign="left",
                valign="middle",
                padding=(dp_scaled(14), 0),
                text_size=(w - dp_scaled(20), None),
            )

            b.size_hint_y = None
            b.height = dp_scaled(60)

            b.bind(on_release=lambda _, f=cb: (f(), self.close()))
            self.panel_content.add_widget(b)

    # --------------------------------------------------
    # Overlay schließen
    # --------------------------------------------------
    def close(self):
        if self.parent:
            self.parent.remove_widget(self)

            if self.parent_header:
                self.parent_header._menu_overlay = None