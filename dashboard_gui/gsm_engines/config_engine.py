# dashboard_gui/config_engine.py
import config
from kivy.clock import Clock

class ConfigEngine:
    def __init__(self, gsm):
        self.gsm = gsm

    def refresh_settings(self):
        """Aktualisiert alle Settings aus config, trimmt Buffers und setzt Intervalle"""
        # 1. Neue Werte aus der Config laden
        new_window = config.get_tile_graph_window()
        new_interval = config.get_refresh_interval()

        # 2. Window-Größen in den Engines setzen
        self.gsm.trend_window = new_window
        self.gsm.max_history = new_window
        
        if hasattr(self.gsm, "graph_engine"):
            self.gsm.graph_engine.window = new_window

        # 3. RSSI Buffer trimmen (Der Fix!)
        # Die History liegt jetzt in der data_flow Engine
        if hasattr(self.gsm, "data_flow"):
            df = self.gsm.data_flow
            # Falls du dort rssi_history hast, trimmen wir sie dort:
            if hasattr(df, "rssi_history"):
                for dev_id in df.rssi_history:
                    buf = df.rssi_history[dev_id]
                    if len(buf) > new_window:
                        df.rssi_history[dev_id] = buf[-new_window:]

        # 4. Global Update Intervall (Clock) neu setzen
        if hasattr(self.gsm, "_main_tick"):
            self.gsm._main_tick.cancel()
            
        # Wir starten den Loop mit dem neuen Intervall frisch
        self.gsm._main_tick = Clock.schedule_interval(self.gsm._global_update, new_interval)

        print(f"[CONFIG] LIVE-SYNC: Fenster={new_window}, Intervall={new_interval}s")