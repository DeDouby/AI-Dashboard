# dashboard_gui/config_engine.py
import config
from kivy.clock import Clock

class ConfigEngine:
    def __init__(self, gsm):
        self.gsm = gsm

    def refresh_settings(self):
        """Aktualisiert alle Settings aus config, trimmt Buffers und setzt Intervalle"""
        self.gsm.trend_window = config.get_tile_graph_window()
        self.gsm.max_history = self.gsm.trend_window
        self.gsm.graph_engine.window = config.get_tile_graph_window()

        # RSSI Buffer trimmen
        for dev in self.gsm.rssi_history:
            buf = self.gsm.rssi_history[dev]
            if len(buf) > self.gsm.max_history:
                self.gsm.rssi_history[dev] = buf[-self.gsm.max_history:]

        # Global Update Intervall
        new_interval = config.get_refresh_interval()
        if hasattr(self.gsm, "_main_tick"):
            self.gsm._main_tick.cancel()
        self.gsm._main_tick = Clock.schedule_interval(self.gsm._global_update, new_interval)

        print(f"[CONFIG] LIVE-SYNC: Fenster={self.gsm.trend_window}, Intervall={new_interval}s")