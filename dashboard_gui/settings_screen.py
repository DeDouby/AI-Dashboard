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
from kivy.metrics import dp
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled

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
        self.header.lbl_title.text = "Settings"
 
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
    # Save Handler - FINAL VERSION
    # -----------------------------
    def _save(self, values: dict):
        cfg = config._init()

        # Standard Parameter
        cfg["refresh_interval"] = float(values.get("refresh_interval", 2.0))
        cfg["ui_refresh_interval"] = float(values.get("ui_refresh_interval", 1.0))
        cfg["stale_timeout"] = float(values.get("stale_timeout", 15.0))
        cfg["tile_graph_window"] = int(values.get("tile_graph_window", 120))
        cfg["temperature_offset"] = float(values.get("temperature_offset", 0.0))
        cfg["humidity_offset"] = float(values.get("humidity_offset", 0.0))
        cfg["leaf_offset"] = float(values.get("leaf_offset", 0.0))
        cfg["temperature_unit"] = values.get("temperature_unit", "C")
        cfg["theme"] = values.get("theme", cfg.get("theme", "tiles"))

        # 🔥 LGS MESH KANÄLE (Neu)
        cfg["lgs_mesh_channel_send"] = int(values.get("lgs_mesh_channel_send", 17))
        cfg["lgs_mesh_channel_recv"] = int(values.get("lgs_mesh_channel_recv", 17))

        # Speichern und Reload der Python-Config
        config.save(cfg)
        config.reload()
        
        # 1. Live Watchdog Update
        from core import _watchdog
        if _watchdog and hasattr(_watchdog, "set_timeout"):
            _watchdog.set_timeout(cfg["stale_timeout"])
            print(f"[SETTINGS] Watchdog stale_timeout live gesetzt → {cfg['stale_timeout']}")
        else:
            print("[SETTINGS] Watchdog live update nicht unterstützt – greift beim Neustart")
        
        # 2. 🔄 Live Tile Graph-Window Update
        import config as _config
        new_window = _config.get_tile_graph_window()
        
        # --- NEU: GSM SYNC ---
        GLOBAL_STATE.refresh_config() 
        # ---------------------
# JETZT den Motor (Global Tick) neu starten!
        # Das aktiviert den neuen refresh_interval sofort live.
        if hasattr(GLOBAL_STATE, "refresh_global_tick"):
            GLOBAL_STATE.refresh_global_tick()
        # ---------------------------------
        dashboard = self.manager.get_screen("dashboard")

        if hasattr(dashboard, "content") and hasattr(dashboard.content, "tile_map"):
            for tile in dashboard.content.tile_map.values():
                if hasattr(tile, "apply_graph_window"):
                    tile.apply_graph_window(new_window)

        # 3. 🚀 HARDWARE RESTART (LGS MESH)
        # Wir nutzen die stabilen Core-Aufrufe wie im Debug-Screen
        import core
        from kivy.utils import platform
        if platform == "android":
            print("[SETTINGS] Triggere Core-Restart für LGS Mesh Kanäle...")
            core.restart_adv_bridge()        # Übernimmt neuen Recv-Kanal (Java-Filter)
            core.restart_broadcast_bridge()  # Übernimmt neuen Send-Kanal (Java-Payload)
        
        # Zurück zum Dashboard
        print("[SETTINGS] Speichervorgang abgeschlossen.")
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
        self.header._last_frame = data
