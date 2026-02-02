# dashboard_gui/ui/grow_rooms_content/grow_room_screen.py
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Rectangle, Color
from kivy.utils import platform
import core
import os

from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled

ASSET_ROOT = os.path.join("dashboard_gui", "assets")

# ---------------- Android-Java Bridge nur auf Android ----------------
if platform == "android":
    from jnius import autoclass
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    ctx = PythonActivity.mActivity
    LogBridge = autoclass('org.hackintosh1980.blebridge.LogBridge')
else:
    PythonActivity = None
    ctx = None
    LogBridge = None


class GrowRoomScreen(Screen):
    name = "grow_rooms"

    def __init__(self, **kw):
        super().__init__(**kw)
        from dashboard_gui.global_state_manager import GLOBAL_STATE
        GLOBAL_STATE.attach_grow_rooms(self)

        # ----------------- Root Layout -----------------
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

        # ----------------- Header -----------------
        self.header = HeaderBar()
        self.header.lbl_title.text = "Grow Rooms"
        self.header.update_back_button("grow_rooms")
        root.add_widget(self.header)

        # ----------------- Scroll Body -----------------
        scroll = ScrollView(do_scroll_x=False)
        body = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=dp_scaled(20),
            spacing=dp_scaled(14)
        )
        body.bind(minimum_height=body.setter("height"))

        # Info Label
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

        # ----------------- LogBridge Buttons -----------------
        btn_restart = Button(text="LogBridge RESTART", size_hint_y=None, height=dp_scaled(56))
        btn_restart.bind(on_release=self.on_logbridge_restart)
        body.add_widget(btn_restart)   # <--- hier hinzufügen

        btn_stop = Button(text="LogBridge STOP", size_hint_y=None, height=dp_scaled(56))
        btn_stop.bind(on_release=self.on_logbridge_stop)
        body.add_widget(btn_stop)      # <--- hier hinzufügen

        scroll.add_widget(body)
        root.add_widget(scroll)
        self.add_widget(root)

    # ------------------------------------------------------------------
    # LogBridge Restart Callback – muss Klassenmethode sein
    # ------------------------------------------------------------------
    def on_logbridge_restart(self, *_):
        print("[UI] LogBridge RESTART pressed")
        try:
            core.restart_log_bridge()
            print("[UI] LogBridge restarted via Core")
        except Exception as e:
            print("[UI] LogBridge restart failed:", e)
    def on_logbridge_stop(self, *_):
        print("[UI] LogBridge STOP pressed")
        try:
            core.stop_log_bridge()
            print("[UI] LogBridge stopped via Core")
        except Exception as e:
            print("[UI] LogBridge stop failed:", e)
    # ------------------------------------------------------------------
    # Update from Global State Manager (Header)
    # ------------------------------------------------------------------
    def update_from_global(self, d):
        self.header.update_from_global(d)
