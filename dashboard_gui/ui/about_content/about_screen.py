# dashboard_gui/about_screen.py
# © 2025 Dominik Rosenthal (Hackintosh1980)

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
import webbrowser

from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.ui.i18n import I18N


class AboutScreen(Screen):
    name = "about"

    def __init__(self, **kw):
        super().__init__(**kw)

        from dashboard_gui.global_state_manager import GLOBAL_STATE
        GLOBAL_STATE.attach_about(self)

        root = BoxLayout(orientation="vertical")

        # HEADER
        self.header = HeaderBar()

        self.header.lbl_title.text = I18N.t("menu.about")
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
            I18N.t("about.version"),
            size=28,
            bold=True
        ))

        body.add_widget(add_label(I18N.t("about.description")))

        link = add_label(
            f"[ref={I18N.t('about.repo_url')}]"
            f"{I18N.t('about.repo_text')}\n"
            f"{I18N.t('about.repo_url')}"
            "[/ref]",
            color=(0.35, 0.65, 1, 1),
            markup=True
        )
        link.bind(on_ref_press=lambda _, url: webbrowser.open(url))
        body.add_widget(link)

        body.add_widget(add_label(
            I18N.t("about.copyright"),
            size=14,
            color=(0.75, 0.75, 0.75, 1)
        ))

        scroll.add_widget(body)
        root.add_widget(scroll)
        self.add_widget(root)

    def update_from_global(self, d):
        self.header.update_from_global(d)
