# dashboard_gui/dashboard.py – SESSION 17 READY

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

import time
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivy.metrics import dp

import config
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.common.control_buttons import ControlButtons
from dashboard_gui.ui.dashboard_content.dashboard_main_panel import DashboardMainPanel
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled


from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.common.header_online import HeaderBar
ASSET_ROOT = os.path.join("dashboard_gui", "assets")

class DashboardScreen(Screen):
    name = "dashboard"

    def __init__(self, **kw):
        super().__init__(**kw)

        # ROOT Layout
        self.root_layout = BoxLayout(orientation="vertical")
        
        # --- HIER: Hintergrund für den VOLLEN Screen ---
        with self.root_layout.canvas.before:
            from kivy.graphics import Rectangle, Color
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(
                source=os.path.join(ASSET_ROOT, "background.png"),
                pos=self.pos,
                size=self.size
            )
        
        self.root_layout.bind(
            pos=lambda *_: setattr(self.bg_rect, "pos", self.root_layout.pos),
            size=lambda *_: setattr(self.bg_rect, "size", self.root_layout.size)
        )
        self.add_widget(self.root_layout)
        # IDIOTENSICHERER PFAD-CACHE
        self._bg_path_1 = os.path.join(ASSET_ROOT, "background.png")
        self._bg_path_2 = os.path.join(ASSET_ROOT, "background2.png")
        # Global State registrieren
        GLOBAL_STATE.ui_handler.attach_screen("dashboard", self) # Geht direkt zum Spezialisten

        # HEADER
        self.header = HeaderBar()
        self.root_layout.add_widget(self.header)

        # MAIN PANEL
        self.content = DashboardMainPanel(size_hint_y=1)
        self.root_layout.add_widget(self.content)
        # nur hinzufügen, ohne Callbacks:
# NEU (mit Verbindung zur Reset-Logik):
        self.controls = ControlButtons(
            on_reset=self.reset_from_global
        )
        self.controls.size_hint = (1,None)
        self.controls.height = dp_scaled(40)
        self.controls.pos_hint = {'y':0}
        self.root_layout.add_widget(self.controls)

        # Tile-Reihenfolge
        self.tile_temp_in = self.content.tile_temp_in
        self.tile_hum_in  = self.content.tile_hum_in
        self.tile_vpd_in  = self.content.tile_vpd_in

        self.tile_temp_ex = self.content.tile_temp_ex
        self.tile_hum_ex  = self.content.tile_hum_ex
        self.tile_vpd_ex  = self.content.tile_vpd_ex

    # ... (Navigation/Picker bleiben identisch)



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
        self.content.update_from_data(d)
    
        # --- ACTIVE TILE CHECK ---
        active_tiles = [k for k, v in self.content.tile_map.items() if v.parent is self.content]
        GLOBAL_STATE.register_tiles(active_tiles)
        is_active = len(active_tiles) > 0
    
        # --- BACKGROUND SWITCH ---
        target_bg = self._bg_path_2 if is_active else self._bg_path_1
    
        if self.bg_rect.source != target_bg:
            self.bg_rect.source = target_bg
        # ------------------------------------
    

    # -----------------------------------------------------
    # GLOBAL RESET
    # -----------------------------------------------------
    def reset_from_global(self):
        """ Sucht alle Graphen im Dashboard und macht sie leer. """
        print("[DASHBOARD] Suche Tiles zum Resetten...")

        # Wir gehen durch ALLE Widgets im Dashboard
        for widget in self.walk():
            # Wenn das Widget eine 'reset' Methode hat (wie deine ChartTiles), ruf sie auf!
            if hasattr(widget, 'reset') and callable(widget.reset):
                widget.reset()

        # Header separat (da dieser meist kein ChartTile ist)
        if hasattr(self, 'header'):
            self.header.set_clock("--:--")
            self.header.set_rssi(None)

    # -----------------------------------------------------
    # TILE → FULLSCREEN
    # -----------------------------------------------------
    def open_fullscreen(self, tile_id):
        fs = self.manager.get_screen("fullscreen")
        fs.activate_tile(tile_id)
        self.manager.current = "fullscreen"





