import os
from kivy.uix.gridlayout import GridLayout
from dashboard_gui.ui.dashboard_content.chart_tile import ChartTile
from dashboard_gui.ui.scaling_utils import dp_scaled
from dashboard_gui.global_state_manager import GLOBAL_STATE

from kivy.uix.scrollview import ScrollView

class DashboardMainPanel(GridLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._gesture_mode = None  # "scroll" oder "swipe"
        self._start_x = 0
        self._start_y = 0
        self.cols = 3
        self.spacing = dp_scaled(12)
        self.padding = dp_scaled(12)
        
        self.size_hint_y = None # Erlaubt dem Panel höher als der Screen zu sein
        self.bind(minimum_height=self.setter('height'))
        # ---------------------------------------------------
        # 1. TILES INITIALISIEREN
        # ---------------------------------------------------
        self.tile_temp_in = ChartTile("temp_in", "Temp IN", "—", [1, 0.2, 0.2, 1], bg="tile_bg_temp_in.png")
        self.tile_hum_in  = ChartTile("hum_in", "Hum IN", "%", [0.2, 0.6, 1, 1], bg="tile_bg_hum_in.png")
        self.tile_vpd_in  = ChartTile("vpd_in", "VPD IN", "kPa", [1, 0.8, 0.2, 1], bg="tile_bg_vpd_in.png")

        self.tile_temp_ex = ChartTile("temp_ex", "Temp EX", "—", [1, 0.4, 0.4, 1], bg="tile_bg_temp_out.png")
        self.tile_hum_ex  = ChartTile("hum_ex", "Hum EX", "%", [0.3, 1, 1, 1], bg="tile_bg_hum_out.png")
        self.tile_vpd_ex  = ChartTile("vpd_ex", "VPD EX", "kPa", [0.3, 1, 0.3, 1], bg="tile_bg_vpd_out.png")

        # NEU: External 2 (Blatt) & Batterie
        self.tile_leaf_temp = ChartTile("leaf_temp", "Leaf Temp", "—", [0.2, 0.8, 0.2, 1], bg="tile_bg_hum_out.png")
        self.tile_vpd_leaf  = ChartTile("vpd_leaf", "VPD Leaf", "kPa", [0.6, 1, 0.2, 1], bg="tile_bg_vpd_out.png")
        # NEU: FAN RPM TILE
        self.tile_fan_rpm   = ChartTile("fan_rpm", "Fan Speed", "RPM", [0.3, 1, 0.3, 1], bg="tile_bg_fan.png")
        self.tile_v_bat     = ChartTile("v_bat", "Battery", "V", [1, 0.8, 0.2, 1], bg="tile_bg_batt.png")

        self.tile_map = {
            "temp_in": self.tile_temp_in, "hum_in": self.tile_hum_in, "vpd_in": self.tile_vpd_in,
            "temp_ex": self.tile_temp_ex, "hum_ex": self.tile_hum_ex, "vpd_ex": self.tile_vpd_ex,
            "leaf_temp": self.tile_leaf_temp, "vpd_leaf": self.tile_vpd_leaf, "fan_rpm": self.tile_fan_rpm, "v_bat": self.tile_v_bat
        }

        for tile in self.tile_map.values():
            self.add_widget(tile)

    def update_from_data(self, d):
        from dashboard_gui.data_buffer import BUFFER
        data = BUFFER.get()
        if not data: return
        
        active_idx = GLOBAL_STATE.get_active_index()
        active_channel = GLOBAL_STATE.get_active_channel()
        active_device_id = data[active_idx].get("device_id") if active_idx < len(data) else None

        # ---------------------------------------------------
        # 2. SICHTBARKEIT (NUR FÜR DAS AKTIVE GERÄT)
        # ---------------------------------------------------
        active_keys = []
        if active_idx < len(data):
            stream = data[active_idx].get(active_channel, {})
            internal = stream.get("internal", {})
            external = stream.get("external", {})
            ext2     = stream.get("external2", {}) # Das Blatt ist jetzt hier!

            # Internal
            if internal.get("temperature", {}).get("value") is not None: active_keys.append("temp_in")
            if internal.get("humidity", {}).get("value") is not None:    active_keys.append("hum_in")
            if stream.get("vpd_internal", {}).get("value") is not None:  active_keys.append("vpd_in")
            
            # External 1 (Luft)
            if external.get("present"):
                if external.get("temperature", {}).get("value") is not None: active_keys.append("temp_ex")
                if external.get("humidity", {}).get("value") is not None:    active_keys.append("hum_ex")
                if stream.get("vpd_external", {}).get("value") is not None:  active_keys.append("vpd_ex")

            # External 2 (Blatt - KOMPLETT UNABHÄNGIG)
            if ext2.get("present"):
                if ext2.get("leaf_temp", {}).get("value") is not None:       active_keys.append("leaf_temp")
                if ext2.get("vpd_leaf", {}).get("value") is not None:        active_keys.append("vpd_leaf")


            # NEU: FAN SICHTBARKEIT (Prüfen ob fan Objekt und speed_rpm da sind)
            fan_data = stream.get("fan", {})
            if fan_data.get("speed_rpm") is not None:
                active_keys.append("fan_rpm")
            
            # Batterie
            if stream.get("battery_voltage") is not None:
                active_keys.append("v_bat")

            self._apply_tile_visibility(active_keys)

        # ---------------------------------------------------
        # 3. WERTE-UPDATE (BUFFER FÜR ALLE GERÄTE)
        # ---------------------------------------------------
        for frame in data:
            device_id = frame.get("device_id")
            stream = frame.get(active_channel)
            if not device_id or not stream or not stream.get("alive"): continue

            prefix = f"{device_id}_{active_channel}"
            is_active = (device_id == active_device_id)

            # Helper-Update Funktion um Code-Müll zu vermeiden
            def u(tile, val_dict, key):
                val = val_dict.get("value") if val_dict else None
                if val is not None:
                    tile.update(val, f"{prefix}_{key}", render=is_active)

            # Internal
            u(self.tile_temp_in, stream.get("internal", {}).get("temperature"), "temp_in")
            u(self.tile_hum_in,  stream.get("internal", {}).get("humidity"), "hum_in")
            u(self.tile_vpd_in,  stream.get("vpd_internal"), "vpd_in")

            # External 1
            ext = stream.get("external", {})
            if ext.get("present"):
                u(self.tile_temp_ex, ext.get("temperature"), "temp_ex")
                u(self.tile_hum_ex,  ext.get("humidity"), "hum_ex")
                u(self.tile_vpd_ex,  stream.get("vpd_external"), "vpd_ex")

            # External 2 (Blatt)
            ext2 = stream.get("external2", {})
            if ext2.get("present"):
                u(self.tile_leaf_temp, ext2.get("leaf_temp"), "leaf_temp")
                u(self.tile_vpd_leaf,  ext2.get("vpd_leaf"), "vpd_leaf")

            # NEU: FAN UPDATE
            fan_rpm = stream.get("fan", {}).get("speed_rpm")
            if fan_rpm is not None:
                self.tile_fan_rpm.update(fan_rpm, f"{prefix}_fan_rpm", render=is_active)

            # Batterie (Spannung direkt aus dem Stream-Root)
            bat_v = stream.get("battery_voltage")
            if bat_v is not None:
                self.tile_v_bat.update(bat_v, f"{prefix}_v_bat", render=is_active)

    def _apply_tile_visibility(self, active_keys):
        self.clear_widgets()
        
        from kivy.core.window import Window
        # Header + Footer Abzug (ca. 150dp)
        offset = dp_scaled(150)
        available_height = Window.height - offset 
        
        num_tiles = len(active_keys)
        
        # Standard Abstände
        base_padding = dp_scaled(12)
        self.padding = [base_padding, base_padding, base_padding, base_padding]
        self.spacing = dp_scaled(12)

        # --- DER DYNAMISCHE SWITCH ---
        if num_tiles <= 3:
            # SZENARIO 1: 1-3 Kacheln -> ECHTES VOLLBILD (Einreihig)
            # Nutzt 100% der verfügbaren Höhe
            row_height = available_height 
            self.rows = 1
        else:
            # SZENARIO 2: Mehr als 3 Kacheln -> 2 REIHEN SICHTBAR (6er Viewport)
            # Alles was drüber ist, landet automatisch in der ScrollView
            row_height = available_height / 2
            self.rows = None # GridLayout darf nach unten wachsen

        order = [
            "temp_in", "hum_in", "vpd_in",
            "temp_ex", "hum_ex", "vpd_ex",
            "leaf_temp", "vpd_leaf", "fan_rpm", "v_bat"
        ]
        
        for key in order:
            if key in active_keys:
                t = self.tile_map[key]
                t.size_hint_y = None
                # Wir ziehen das vertikale Spacing ab, damit nichts unten rausguckt
                t.height = row_height - self.spacing[1]
                self.add_widget(t)


    # GESTURE DELEGATION
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._gesture_mode = None
            self._start_x = touch.x
            self._start_y = touch.y
    
            if hasattr(GLOBAL_STATE, "ggm"):
                GLOBAL_STATE.ggm.handle_touch("dashboard", "down", touch)
    
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if hasattr(GLOBAL_STATE, "ggm"):
            handled = GLOBAL_STATE.ggm.handle_touch("dashboard", "move", touch)
            if handled:
                return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if hasattr(GLOBAL_STATE, "ggm"):
            handled = GLOBAL_STATE.ggm.handle_touch("dashboard", "up", touch)
            if handled:
                return True
        return super().on_touch_up(touch)