# dashboard_gui/ui/grow_rooms_content/grow_room_screen.py
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Rectangle, Color
import os

from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled

ASSET_ROOT = os.path.join("dashboard_gui", "assets")

class GrowRoomScreen(Screen):
    name = "grow_rooms"

    def __init__(self, **kw):
        super().__init__(**kw)
        from dashboard_gui.global_state_manager import GLOBAL_STATE
        GLOBAL_STATE.attach_grow_rooms(self)

        root = BoxLayout(orientation="vertical")
        with root.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(
                source=os.path.join(ASSET_ROOT, "background.png"),
                pos=root.pos,
                size=root.size
            )
        root.bind(
            pos=lambda *_: setattr(self.bg_rect, "pos", root.pos),
            size=lambda *_: setattr(self.bg_rect, "size", root.size)
        )

        # HEADER
        self.header = HeaderBar()
        self.header.lbl_title.text = "Grow Rooms"
        self.header.update_back_button("grow_rooms")
        root.add_widget(self.header)

        # SCROLLVIEW
        scroll = ScrollView(do_scroll_x=False)
        body = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=dp_scaled(20),
            spacing=dp_scaled(14)
        )
        body.bind(minimum_height=body.setter("height"))

        # Platzhalter-Label
        lbl = Label(
            text="Hier erscheinen später die Grow Rooms Infos...",
            font_size=sp_scaled(18),
            color=(1, 1, 1, 1),
            halign="center",
            valign="top",
            size_hint_y=None
        )
        lbl.bind(
            width=lambda i, w: setattr(i, "text_size", (w - dp_scaled(40), None)),
            texture_size=lambda i, ts: setattr(i, "height", ts[1])
        )
        body.add_widget(lbl)

        scroll.add_widget(body)
        root.add_widget(scroll)
        self.add_widget(root)

    def update_from_global(self, d):
        self.header.update_from_global(d)