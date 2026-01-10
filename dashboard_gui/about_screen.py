# dashboard_gui/about_screen.py
# © 2025 Dominik Rosenthal (Hackintosh1980)

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
import webbrowser

from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled


class AboutScreen(Screen):
    name = "about"

    def __init__(self, **kw):
        super().__init__(**kw)

        from dashboard_gui.global_state_manager import GLOBAL_STATE
        GLOBAL_STATE.attach_about(self)

        root = BoxLayout(orientation="vertical")

        # HEADER
        self.header = HeaderBar(
            goto_setup=lambda *_: setattr(self.manager, "current", "setup"),
            goto_debug=lambda *_: setattr(self.manager, "current", "debug"),
            goto_device_picker=lambda *_: setattr(self.manager, "current", "device_picker"),
        )
        self.header.lbl_title.text = "About"
        self.header.update_back_button("about")
        root.add_widget(self.header)

        # SCROLL
        scroll = ScrollView(do_scroll_x=False)

        body = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=dp_scaled(20),
            spacing=dp_scaled(14)
        )
        body.bind(minimum_height=body.setter("height"))

        def add_label(text, size=16, color=(1, 1, 1, 1), markup=False, bold=False):
            lbl = Label(
                text=text,
                font_size=sp_scaled(size),
                color=color,
                markup=markup,
                bold=bold,
                halign="left",
                valign="top",
                size_hint_y=None
            )
            lbl.bind(texture_size=lambda i, *_: setattr(i, "height", i.texture_size[1]))
            return lbl

        body.add_widget(add_label(
            "ManoVerde Panel 1.24",
            size=28,
            bold=True
        ))

        body.add_widget(add_label(
            "Manoverde es un sistema de monitorización y análisis para sensores "
            "Bluetooth Low Energy (BLE).\n\n"
            "Unifica datos de diferentes fabricantes y protocolos "
            "(ADV, GATT, dispositivos híbridos) en un modelo único y consistente.\n\n"
            "Se centra en señales en tiempo real, control explícito y configuración "
            "transparente — sin automatizaciones ocultas.\n\n"
            "Manoverde interpreta los dispositivos tal como se comportan, "
            "sin forzarlos a abstracciones simplificadas.\n\n"
            "Bluetooth es necesario para detectar y leer los sensores. "
            "Actívalo y concede los permisos solicitados."
        ))

        link = add_label(
            "[ref=https://github.com/Hackintosh1980/AI-Dashboard]"
            "Project & Updates:\n"
            "https://github.com/Hackintosh1980/AI-Dashboard"
            "[/ref]",
            color=(0.35, 0.65, 1, 1),
            markup=True
        )
        link.bind(on_ref_press=lambda _, url: webbrowser.open(url))
        body.add_widget(link)

        body.add_widget(add_label(
            "© 2025 Dominik Rosenthal (Hackintosh1980)",
            size=14,
            color=(0.75, 0.75, 0.75, 1)
        ))

        scroll.add_widget(body)
        root.add_widget(scroll)
        self.add_widget(root)

    def update_from_global(self, d):
        self.header.update_from_global(d)
