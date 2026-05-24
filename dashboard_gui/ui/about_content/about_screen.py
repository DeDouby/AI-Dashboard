# dashboard_gui/about_screen.py
# © 2025 Dominik Rosenthal (Hackintosh1980)

import os
import webbrowser
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Rectangle, Color
from kivy.uix.modalview import ModalView
from kivy.uix.image import Image
from kivy.metrics import dp
from kivy.animation import Animation # Oben bei den Imports hinzufügen
from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.ui.i18n import I18N

ASSET_ROOT = os.path.join("dashboard_gui", "assets")

class AboutScreen(Screen):
    name = "about"

    def __init__(self, **kw):
        super().__init__(**kw)
        self.click_count = 0
        
        # 1. Erst die Hilfsfunktion definieren
        def add_label(text, size=16, color=(1, 1, 1, 1), markup=False, bold=False):
            lbl = Label(
                text=text, font_size=sp_scaled(size), color=color, markup=markup,
                halign="center", valign="top", size_hint_y=None, bold=bold
            )
            lbl.bind(
                width=lambda i, w: setattr(i, "text_size", (w - dp_scaled(40), None)),
                texture_size=lambda i, ts: setattr(i, "height", ts[1])
            )
            return lbl

        # 2. Setup UI Struktur
        from dashboard_gui.global_state_manager import GLOBAL_STATE
        GLOBAL_STATE.ui_handler.attach_screen("about", self)

        root = BoxLayout(orientation="vertical")
        with root.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(source=os.path.join(ASSET_ROOT, "background_about.png"), pos=root.pos, size=root.size)
        
        root.bind(pos=lambda *_: setattr(self.bg_rect, "pos", root.pos), size=lambda *_: setattr(self.bg_rect, "size", root.size))
        
        self.header = HeaderBar()
        self.header.lbl_title.text = I18N.t("menu.about")
        self.header.update_back_button("about")
        root.add_widget(self.header)

        scroll = ScrollView(do_scroll_x=False)
        body = BoxLayout(orientation="vertical", size_hint_y=None, padding=dp_scaled(20), spacing=dp_scaled(14))
        body.bind(minimum_height=body.setter("height"))

        # 3. Easter Egg Logik
        def show_tina(instance, touch):
            if instance.collide_point(*touch.pos):
                self.click_count += 1
                if self.click_count >= 7:
                    self.click_count = 0
                    popup = ModalView(size_hint=(0.8, 0.8), background='')
                    popup.add_widget(Image(source=os.path.join(ASSET_ROOT, "tina.png")))
                    popup.open()

        # 4. Widgets hinzufügen
        version_lbl = add_label(I18N.t("about.version"), size=28, bold=True)
        version_lbl.bind(on_touch_down=show_tina)
        body.add_widget(version_lbl)

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
        
        community_link = add_label(
            f"[ref={I18N.t('about.community_url')}]"
            f"{I18N.t('about.community_text')}\n"
            f"{I18N.t('about.community_name')}"
            "[/ref]",
            color=(0.45, 0.82, 1, 1),
            markup=True
        )
        community_link.bind(on_ref_press=lambda _, url: webbrowser.open(url))
        body.add_widget(community_link)

        body.add_widget(add_label(I18N.t("about.copyright"), size=14, color=(0.75, 0.75, 0.75, 1)))

        scroll.add_widget(body)
        root.add_widget(scroll)
        self.add_widget(root)

    def update_from_global(self, d):
        self.header.update_from_global(d)