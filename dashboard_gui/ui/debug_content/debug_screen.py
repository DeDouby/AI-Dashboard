#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen
from kivy.metrics import dp
from kivy.utils import platform
from kivy.clock import Clock

from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.global_state_manager import GLOBAL_STATE
import core  # Dein Core-Modul


class DebugScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)

        # -----------------------------
        # ROOT LAYOUT
        # -----------------------------
        root = BoxLayout(orientation="vertical")
        self.add_widget(root)

        # -----------------------------
        # HEADER FIX OBEN
        # -----------------------------
        self.header = HeaderBar()
        self.header.lbl_title.text = "Debug"

        self.header.enable_back("dashboard")
        root.add_widget(self.header)
        GLOBAL_STATE.ui_handler.attach_screen("debug", self)

        # -----------------------------
        # BUTTONS IN SCROLLVIEW
        # -----------------------------
        from kivy.uix.scrollview import ScrollView
        scroll = ScrollView(size_hint=(1, 1))
        root.add_widget(scroll)

        btn_container = BoxLayout(orientation="vertical",
                                  spacing=dp_scaled(10),
                                  padding=dp_scaled(12),
                                  size_hint_y=None)
        btn_container.bind(minimum_height=btn_container.setter("height"))
        scroll.add_widget(btn_container)

        def mk_btn(label, cb, base_color):
        
            btn = Button(
                text=label,
                background_normal="",
                background_down="",
                background_color=(*base_color[:3], 0.60),
                font_size=sp_scaled(18),
                size_hint_y=None,
                height=dp_scaled(50),
            )
        
            # klick feedback wie settings
            btn.bind(on_release=lambda b, c=base_color, fn=cb: self._flash_and_run(b, c, fn))
        
            return btn
        # ADV
        btn_container.add_widget(
            mk_btn("ADV STOP", lambda: core.stop_adv_bridge(), (0.40, 0.10, 0.10, 1))
        )
        btn_container.add_widget(
            mk_btn("ADV RESTART", lambda: core.restart_adv_bridge(), (0.12, 0.20, 0.45, 1))
        )
        
        # GATT
        btn_container.add_widget(
            mk_btn("GATT STOP", lambda: core.stop_gatt_bridge(), (0.40, 0.10, 0.10, 1))
        )
        btn_container.add_widget(
            mk_btn("GATT RESTART", lambda: core.restart_gatt_bridge(), (0.12, 0.20, 0.45, 1))
        )
        
        # LOG
        btn_container.add_widget(
            mk_btn("LOG STOP", lambda: core.stop_log_bridge(), (0.40, 0.10, 0.10, 1))
        )
        btn_container.add_widget(
            mk_btn("LOG RESTART", lambda: core.restart_log_bridge(), (0.12, 0.20, 0.45, 1))
        )
        # BROADCAST (LGS Mesh)
        btn_container.add_widget(
            mk_btn("BROADCAST STOP", lambda: core.stop_broadcast_bridge(), (0.45, 0.25, 0.05, 1)) # Braun/Orange für Sendebetrieb
        )
        btn_container.add_widget(
            mk_btn("BROADCAST RESTART", lambda: core.restart_broadcast_bridge(), (0.12, 0.20, 0.45, 1))
        )        
        # SYSTEM
        btn_container.add_widget(
            mk_btn("SYSTEM STOP", lambda: core.stop(), (0.40, 0.10, 0.10, 1))
        )
        btn_container.add_widget(
            mk_btn("SYSTEM RESTART", lambda: core.start(), (0.12, 0.20, 0.45, 1))
        )
        
    # --------------------------
    # Press / Release Feedback
    # --------------------------
    def _flash_and_run(self, btn, base_color, callback):
        r, g, b, _ = base_color
    
        # Heller = Klick sichtbar
        btn.background_color = (min(r+0.25,1), min(g+0.25,1), min(b+0.25,1), 1)
    
        def _restore(dt):
            btn.background_color = (r, g, b, 0.6)
            if callback:
                callback()
    
        # exakt das macht Settings Gefühl:
        Clock.schedule_once(_restore, 0.12)

    def update_from_global(self, d):
        self.header.update_from_global(d)
