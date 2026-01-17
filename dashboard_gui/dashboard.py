# dashboard_gui/dashboard.py – SESSION 17 READY

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen

import config
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.common.control_buttons import ControlButtons
from dashboard_gui.ui.dashboard_content.dashboard_main_panel import DashboardMainPanel


from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.common.header_online import HeaderBar

class DashboardScreen(Screen):
    name = "dashboard"

    def __init__(self, **kw):
        super().__init__(**kw)

        # ROOT Layout
        root = BoxLayout(orientation="vertical")
        self.add_widget(root)

        # Global State registrieren
        GLOBAL_STATE.attach_dashboard(self)

        # HEADER
        self.header = HeaderBar()
        root.add_widget(self.header)

        # MAIN PANEL → nur ein Panel verwenden
        self.content = DashboardMainPanel(size_hint_y=1)
        root.add_widget(self.content)

        # CONTROL BUTTONS
        self.controls = ControlButtons(
            on_start=lambda *_: GLOBAL_STATE.start(),
            on_stop=lambda *_: GLOBAL_STATE.stop(),
            on_reset=lambda *_: GLOBAL_STATE.reset()
        )
        root.add_widget(self.controls)

        # Tile-Reihenfolge
        self.tile_temp_in = self.content.tile_temp_in
        self.tile_hum_in  = self.content.tile_hum_in
        self.tile_vpd_in  = self.content.tile_vpd_in

        self.tile_temp_ex = self.content.tile_temp_ex
        self.tile_hum_ex  = self.content.tile_hum_ex
        self.tile_vpd_ex  = self.content.tile_vpd_ex

    # -----------------------------------------------------
    # Navigation
    # -----------------------------------------------------
    def goto_setup(self, *_):
        self.manager.current = "setup"

    def goto_debug(self, *_):
        self.manager.current = "debug"

    # -----------------------------------------------------
    # OPEN DEVICE PICKER
    # -----------------------------------------------------
    def open_device_picker(self, *_):
        """
        Wird von HeaderBar aufgerufen, wenn der User ⇅ klickt.
        """
        picker = self.manager.get_screen("device_picker")
        picker.open()
        self.manager.current = "device_picker"


    # -----------------------------------------------------
    # GLOBAL TICK → Dashboard Update
    # -----------------------------------------------------
    def update_from_global(self, d):
        self.header.update_from_global(d)

        # PANELS / TILES
        self.content.update_from_data(d)


    # -----------------------------------------------------
    # GLOBAL RESET
    # -----------------------------------------------------
    def reset_from_global(self):
        print("[DASHBOARD] Resetting…")

        # Tiles resetten
        self.tile_temp_in.reset()
        self.tile_hum_in.reset()
        self.tile_vpd_in.reset()

        self.tile_temp_ex.reset()
        self.tile_hum_ex.reset()
        self.tile_vpd_ex.reset()

        # Header minimal
        self.header.set_clock("--:--")
        self.header.set_rssi(None)

        # LED kommt vom GSM


    # -----------------------------------------------------
    # TILE → FULLSCREEN
    # -----------------------------------------------------
    def open_fullscreen(self, tile_id):
        fs = self.manager.get_screen("fullscreen")
        fs.activate_tile(tile_id)
        self.manager.current = "fullscreen"


    # -----------------------------------------------------
    # Dummy-API (Dashboard ist GSM-Driven)
    # -----------------------------------------------------
    def start_updates(self):
        pass

    def stop_updates(self):
        pass


