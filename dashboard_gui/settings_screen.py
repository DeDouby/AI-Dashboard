# -*- coding: utf-8 -*-
"""
SettingsScreen – zentrale Einstellungsseite
© 2025-2026 Dominik Rosenthal (Hackintosh1980)
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.settings_content.settings_main_panel import SettingsMainPanel
import config
from dashboard_gui.ui.i18n import I18N

class SettingsScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)

        # Root Layout
        root = BoxLayout(orientation="vertical")

        # Attach to global state
        GLOBAL_STATE.attach_settings(self)

        # Header Bar
        self.header = HeaderBar()

        self.header.update_back_button("settings")
        root.add_widget(self.header)

        # Settings Panel
        panel = SettingsMainPanel(
            on_save=self._save,
            on_cancel=self._cancel
        )
        # Set current language
        I18N.init()
        panel_inputs = panel.inputs  # Zugriff auf Inputs falls nötig
        root.add_widget(panel)

        self.add_widget(root)

    # -----------------------------
    # Save Handler
    # -----------------------------
    def _save(self, values: dict):
        cfg = config._init()

        cfg["refresh_interval"] = float(values.get("refresh_interval",2.0))
        cfg["ui_refresh_interval"] = float(values.get("ui_refresh_interval",1.0))
        cfg["stale_timeout"] = float(values.get("stale_timeout",15.0))
        cfg["tile_graph_window"] = int(values.get("tile_graph_window",120))
        cfg["temperature_offset"] = float(values.get("temperature_offset",0.0))
        cfg["humidity_offset"] = float(values.get("humidity_offset",0.0))
        cfg["leaf_offset"] = float(values.get("leaf_offset",0.0))

        cfg["temperature_unit"] = values.get("temperature_unit","C")

        config.save(cfg)
        config.reload()
        
        # Live Watchdog update
        from core import _watchdog
        
        if _watchdog and hasattr(_watchdog, "set_timeout"):
            _watchdog.set_timeout(cfg["stale_timeout"])
            print(f"[SETTINGS] Watchdog stale_timeout live gesetzt → {cfg['stale_timeout']}")
        else:
            print("[SETTINGS] Watchdog live update nicht unterstützt – greift beim Neustart")
        
        # 🔄 Live Tile Graph-Window Update
        import config as _config
        new_window = _config.get_tile_graph_window()
        
        dashboard = self.manager.get_screen("dashboard")
        for tile in dashboard.content.tile_map.values():
            if hasattr(tile, "apply_graph_window"):
                tile.apply_graph_window(new_window)
        
        # Back to dashboard
        self.manager.current = "dashboard"
    # -----------------------------
    # Cancel Handler
    # -----------------------------
    def _cancel(self, *_):
        self.manager.current = "dashboard"

    # -----------------------------
    # Update UI from global state
    # -----------------------------
    def update_from_global(self, data):
        self.header.update_from_global(data)
