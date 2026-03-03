import os
from kivy.uix.gridlayout import GridLayout
from kivy.graphics import Rectangle, Color
from dashboard_gui.ui.dashboard_content.chart_tile import ChartTile
from dashboard_gui.ui.scaling_utils import dp_scaled
from kivy.animation import Animation
from dashboard_gui.global_state_manager import GLOBAL_STATE
ASSET_ROOT = os.path.join("dashboard_gui", "assets")

class DashboardMainPanel(GridLayout):
    def __init__(self, **kw):
        super().__init__(**kw)


        self.cols = 3
        self.spacing = dp_scaled(12)
        self.padding = dp_scaled(12)

# ---------------------------------------------------
        # IN SENSORS
        # ---------------------------------------------------
        self.tile_temp_in = ChartTile(
            "temp_in", "Temperature IN", "—",
            [1, 0.2, 0.2, 1],
            bg="tile_bg_temp_in.png",
        )
        self.tile_hum_in = ChartTile(
            "hum_in", "Humidity IN", "%",
            [0.2, 0.6, 1, 1],
            bg="tile_bg_hum_in.png",
        )
        self.tile_vpd_in = ChartTile(
            "vpd_in", "VPD IN", "kPa",
            [1, 0.8, 0.2, 1],
            bg="tile_bg_vpd_in.png",
        )

        # ---------------------------------------------------
        # EX SENSORS
        # ---------------------------------------------------
        self.tile_temp_ex = ChartTile(
            "temp_ex", "Temperature EX", "—",
            [1, 0.4, 0.4, 1],
            bg="tile_bg_temp_out.png",
        )
        self.tile_hum_ex = ChartTile(
            "hum_ex", "Humidity EX", "%",
            [0.3, 1, 1, 1],
            bg="tile_bg_hum_out.png",
        )
        self.tile_vpd_ex = ChartTile(
            "vpd_ex", "VPD EX", "kPa",
            [0.3, 1, 0.3, 1],
            bg="tile_bg_vpd_out.png",
        )

        # Map bleibt gleich, da die Variablennamen stimmen
        self.tile_map = {
            "temp_in": self.tile_temp_in,
            "hum_in":  self.tile_hum_in,
            "vpd_in":  self.tile_vpd_in,
            "temp_ex": self.tile_temp_ex,
            "hum_ex":  self.tile_hum_ex,
            "vpd_ex":  self.tile_vpd_ex,
        }
        # ---------------------------------------------------
        # SWIPE STATE (ADD ONLY)
        # ---------------------------------------------------
        self._touch_start_x = None
        self._touch_active = False
        self._swipe_threshold = dp_scaled(60)

        # Anfang: alles anzeigen
        for tile in self.tile_map.values():
            self.add_widget(tile)

    # ============================================================
    # UPDATE – PURE MODE (decoded = Quelle, 1:1 übernehmen)
    # ============================================================
    def update_from_data(self, d):
        if not isinstance(d, dict):
            return
    
        from dashboard_gui.data_buffer import BUFFER
        from dashboard_gui.global_state_manager import GLOBAL_STATE
    
        data = BUFFER.get()
        if not data:
            return
        
        active_channel = GLOBAL_STATE.get_active_channel()
        
        active_idx = GLOBAL_STATE.get_active_index()
        active_device_id = (
            data[active_idx].get("device_id")
            if active_idx < len(data) else None
        )
    
        active_channel = GLOBAL_STATE.get_active_channel()
    
        # Sichtbarkeit NUR fürs aktive Gerät
        self._apply_tile_visibility([])
    
        active_idx = GLOBAL_STATE.get_active_index()
        if active_idx < len(data):
            frame = data[active_idx]
            stream = frame.get(active_channel, {})
            internal = stream.get("internal", {})
            external = stream.get("external", {})
            vpd_int = stream.get("vpd_internal", {})
            vpd_ext = stream.get("vpd_external", {})
    
            active = []
            if internal.get("temperature", {}).get("value") is not None:
                active.append("temp_in")
            if internal.get("humidity", {}).get("value") is not None:
                active.append("hum_in")
            if vpd_int.get("value") is not None:
                active.append("vpd_in")
            if external.get("present"):
                if external.get("temperature", {}).get("value") is not None:
                    active.append("temp_ex")
                if external.get("humidity", {}).get("value") is not None:
                    active.append("hum_ex")
                if vpd_ext.get("value") is not None:
                    active.append("vpd_ex")
    
            self._apply_tile_visibility(active)
    
        # 🔥 BUFFER FÜR ALLE GERÄTE
        for frame in data:
            device_id = frame.get("device_id")
            if not device_id:
                continue
    
            stream = frame.get(active_channel)
            if not stream or not stream.get("alive"):
                continue
    
            prefix = f"{device_id}_{active_channel}"
    
            internal = stream.get("internal", {})
            external = stream.get("external", {})
            vpd_int = stream.get("vpd_internal", {})
            vpd_ext = stream.get("vpd_external", {})
    
            if internal.get("temperature", {}).get("value") is not None:
                self.tile_temp_in.update(
                    internal["temperature"]["value"],
                    f"{prefix}_temp_in",
                    render=(device_id == active_device_id)
                )
            
            if internal.get("humidity", {}).get("value") is not None:
                self.tile_hum_in.update(
                    internal["humidity"]["value"],
                    f"{prefix}_hum_in",
                    render=(device_id == active_device_id)
                )
            
            if vpd_int.get("value") is not None:
                self.tile_vpd_in.update(
                    vpd_int["value"],
                    f"{prefix}_vpd_in",
                    render=(device_id == active_device_id)
                )
            
            if external.get("present") and external.get("temperature", {}).get("value") is not None:
                self.tile_temp_ex.update(
                    external["temperature"]["value"],
                    f"{prefix}_temp_ex",
                    render=(device_id == active_device_id)
                )
            
                if external.get("humidity", {}).get("value") is not None:
                    self.tile_hum_ex.update(
                        external["humidity"]["value"],
                        f"{prefix}_hum_ex",
                        render=(device_id == active_device_id)
                    )
            
                if vpd_ext.get("value") is not None:
                    self.tile_vpd_ex.update(
                        vpd_ext["value"],
                        f"{prefix}_vpd_ex",
                        render=(device_id == active_device_id)
                    )

    # ============================================================
    # Sichtbarkeit
    # ============================================================
    def _apply_tile_visibility(self, active_keys):
        self.clear_widgets()
      
        # Tiles in gewünschter Reihenfolge hinzufügen
        order = [
            "temp_in", "hum_in", "vpd_in",
            "temp_ex", "hum_ex", "vpd_ex",
        ]
    
        for key in order:
            if key in active_keys:
                self.add_widget(self.tile_map[key])
    # ============================================================
    # DEVICE SWIPE (HORIZONTAL)
    # ============================================================

    def get_active_tile_keys(self):
        return [k for k, v in self.tile_map.items() if v.parent is self]   

    # ============================================================
    # GLOBAL SWIPE DELEGATION
    # ============================================================
    
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if hasattr(GLOBAL_STATE, "swipe_engine"):
                GLOBAL_STATE.swipe_engine.process_touch_down(touch)
        return super().on_touch_down(touch)
    
    
    def on_touch_move(self, touch):
        if hasattr(GLOBAL_STATE, "swipe_engine"):
            GLOBAL_STATE.swipe_engine.process_touch_move(touch)
        return super().on_touch_move(touch)
    
    
    def on_touch_up(self, touch):
        if hasattr(GLOBAL_STATE, "swipe_engine"):
            GLOBAL_STATE.swipe_engine.process_touch_up(touch)
        return super().on_touch_up(touch)