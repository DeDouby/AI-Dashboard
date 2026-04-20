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
        # --- NEU: BLE SENSOR TILES ---
        self.tile_ble_temp_sps = ChartTile("ble_temp_sps", "SPS Temp", "—", [1, 0.2, 0.5, 1], bg="tile_bg_temp_in.png")
        self.tile_ble_hum_sps  = ChartTile("ble_hum_sps", "SPS Hum", "%", [0.2, 0.8, 1, 1], bg="tile_bg_hum_in.png")
        # --- NEU: BLE VPD TILES ---
        self.tile_ble_vpd_sps = ChartTile("ble_vpd_sps", "SPS VPD", "kPa", [0.6, 0.4, 1, 1], bg="tile_bg_vpd_in.png")
        self.tile_ble_vpd_tb2 = ChartTile("ble_vpd_tb2", "TB2 VPD", "kPa", [0.4, 0.6, 1, 1], bg="tile_bg_vpd_out.png")
        
        self.tile_ble_temp_tb2 = ChartTile("ble_temp_tb2", "TB2 Temp", "—", [1, 0.5, 0.2, 1], bg="tile_bg_temp_in.png")
        self.tile_ble_hum_tb2  = ChartTile("ble_hum_tb2", "TB2 Hum", "%", [0.5, 0.8, 1, 1], bg="tile_bg_hum_in.png")
        # NEU: External 2 (Blatt) & Batterie
        self.tile_leaf_temp = ChartTile("leaf_temp", "Leaf Temp", "—", [0.2, 0.8, 0.2, 1], bg="tile_bg_hum_out.png")
        self.tile_vpd_leaf  = ChartTile("vpd_leaf", "VPD Leaf", "kPa", [0.6, 1, 0.2, 1], bg="tile_bg_vpd_out.png")
        
        # NEU: FAN RPM TILE
        self.tile_circulation_fan_rpm   = ChartTile("circulation_fan_rpm", "Circulation Fan Speed", "RPM", [0.3, 1, 0.3, 1], bg="tile_bg_fan.png")
        self.tile_exhaust_fan_rpm   = ChartTile("exhaust_fan_rpm", "Exhaust Fan Speed", "RPM", [0.3, 1, 0.3, 1], bg="tile_bg_fan.png")
        
        self.tile_v_bat     = ChartTile("v_bat", "Battery", "V", [1, 0.8, 0.2, 1], bg="tile_bg_batt.png")

        self.tile_map = {
            "temp_in": self.tile_temp_in, "hum_in": self.tile_hum_in, "vpd_in": self.tile_vpd_in,
            "temp_ex": self.tile_temp_ex, "hum_ex": self.tile_hum_ex, "vpd_ex": self.tile_vpd_ex,
            "leaf_temp": self.tile_leaf_temp, "vpd_leaf": self.tile_vpd_leaf, 
            "circulation_fan_rpm": self.tile_circulation_fan_rpm, "exhaust_fan_rpm": self.tile_exhaust_fan_rpm, 
            "v_bat": self.tile_v_bat,
            
            # BLE Tiles - Namen müssen exakt mit 'active_keys' und 'order' übereinstimmen
            "ble_temp_sps": self.tile_ble_temp_sps,
            "ble_hum_sps":  self.tile_ble_hum_sps,
            "ble_vpd_sps":  self.tile_ble_vpd_sps, # HIER KORRIGIERTSPS hast
            
            "ble_temp_tb2": self.tile_ble_temp_tb2,
            "ble_hum_tb2":  self.tile_ble_hum_tb2,
            "ble_vpd_tb2":  self.tile_ble_vpd_tb2  # HIER KORRIGIERTD Tile für TB2 hast
        }



    def update_from_data(self, d):  
        from dashboard_gui.data_buffer import BUFFER
        data = BUFFER.get()
        if not data: return
        
        active_idx = GLOBAL_STATE.get_active_index()
        active_channel = GLOBAL_STATE.get_active_channel()
        active_device_id = data[active_idx].get("device_id") if active_idx < len(data) else None

        # Helper-Update Funktion (JETZT GANZ OBEN DEFINIERT)
        # So ist sie in der ganzen Methode verfügbar.
        def u(tile, val_dict, key, prefix, is_active):
            val = val_dict.get("value") if (val_dict and isinstance(val_dict, dict)) else None
            if val is not None:
                tile.update(val, f"{prefix}_{key}", render=is_active)

        # ---------------------------------------------------
        # 2. SICHTBARKEIT (NUR FÜR DAS AKTIVE GERÄT)
        # ---------------------------------------------------
        active_keys = []
        if active_idx < len(data):
            stream = data[active_idx].get(active_channel, {})
            internal = stream.get("internal", {})
            external = stream.get("external", {})
            ext2     = stream.get("external2", {})
            ble      = stream.get("ble_sensors", {})

            # Check Internal
            if internal.get("temperature", {}).get("value") is not None: active_keys.append("temp_in")
            if internal.get("humidity", {}).get("value") is not None:    active_keys.append("hum_in")
            if stream.get("vpd_internal", {}).get("value") is not None:  active_keys.append("vpd_in")
            
            # Check External 1
            if external.get("present"):
                if external.get("temperature", {}).get("value") is not None: active_keys.append("temp_ex")
                if external.get("humidity", {}).get("value") is not None:    active_keys.append("hum_ex")
                if stream.get("vpd_external", {}).get("value") is not None:  active_keys.append("vpd_ex")

            # Check External 2 (Leaf)
            if ext2.get("present"):
                if ext2.get("leaf_temp", {}).get("value") is not None:       active_keys.append("leaf_temp")
                if ext2.get("vpd_leaf", {}).get("value") is not None:        active_keys.append("vpd_leaf")

            # Check BLE Sensors
            sps_data = ble.get("sps", {})
            if sps_data.get("online"):
                if sps_data.get("temperature", {}).get("value") is not None: active_keys.append("ble_temp_sps")
                if sps_data.get("humidity", {}).get("value") is not None:    active_keys.append("ble_hum_sps")
                if sps_data.get("vpd", {}).get("value") is not None:         active_keys.append("ble_vpd_sps") # NEU


            tb2_data = ble.get("tb2", {})
            if tb2_data.get("online"):
                if tb2_data.get("temperature", {}).get("value") is not None: active_keys.append("ble_temp_tb2")
                if tb2_data.get("humidity", {}).get("value") is not None:    active_keys.append("ble_hum_tb2")
                if tb2_data.get("vpd", {}).get("value") is not None:         active_keys.append("ble_vpd_tb2") # NEU
            # Check Fans & Battery
            if stream.get("circulation_fan", {}).get("circulation_fan_rpm") is not None: active_keys.append("circulation_fan_rpm")
            if stream.get("exhaust_fan", {}).get("exhaust_fan_rpm") is not None:         active_keys.append("exhaust_fan_rpm")
            if stream.get("battery_voltage") is not None:                               active_keys.append("v_bat")

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
            ble = stream.get("ble_sensors", {})

            # Internal
            u(self.tile_temp_in, stream.get("internal", {}).get("temperature"), "temp_in", prefix, is_active)
            u(self.tile_hum_in,  stream.get("internal", {}).get("humidity"), "hum_in", prefix, is_active)
            u(self.tile_vpd_in,  stream.get("vpd_internal"), "vpd_in", prefix, is_active)

            # External 1
            ext = stream.get("external", {})
            if ext.get("present"):
                u(self.tile_temp_ex, ext.get("temperature"), "temp_ex", prefix, is_active)
                u(self.tile_hum_ex,  ext.get("humidity"), "hum_ex", prefix, is_active)
                u(self.tile_vpd_ex,  stream.get("vpd_external"), "vpd_ex", prefix, is_active)

            # External 2
            ext2 = stream.get("external2", {})
            if ext2.get("present"):
                u(self.tile_leaf_temp, ext2.get("leaf_temp"), "leaf_temp", prefix, is_active)
                u(self.tile_vpd_leaf,  ext2.get("vpd_leaf"), "vpd_leaf", prefix, is_active)

            # BLE SPS
            sps = ble.get("sps", {})
            u(self.tile_ble_temp_sps, sps.get("temperature"), "ble_temp_sps", prefix, is_active)
            u(self.tile_ble_hum_sps,  sps.get("humidity"), "ble_hum_sps", prefix, is_active)
            u(self.tile_ble_vpd_sps,  sps.get("vpd"), "ble_vpd_sps", prefix, is_active) # NEU
            # BLE TB2
            tb2 = ble.get("tb2", {})
            u(self.tile_ble_temp_tb2, tb2.get("temperature"), "ble_temp_tb2", prefix, is_active)
            u(self.tile_ble_hum_tb2,  tb2.get("humidity"), "ble_hum_tb2", prefix, is_active)
            u(self.tile_ble_vpd_tb2,  tb2.get("vpd"), "ble_vpd_tb2", prefix, is_active) # NEU
            # Fans & Battery
            circ_rpm = stream.get("circulation_fan", {}).get("circulation_fan_rpm")
            if circ_rpm is not None:
                self.tile_circulation_fan_rpm.update(circ_rpm, f"{prefix}_circulation_fan_rpm", render=is_active)

            exh_rpm = stream.get("exhaust_fan", {}).get("exhaust_fan_rpm")
            if exh_rpm is not None:
                self.tile_exhaust_fan_rpm.update(exh_rpm, f"{prefix}_exhaust_fan_rpm", render=is_active)

            bat_v = stream.get("battery_voltage")
            if bat_v is not None:
                self.tile_v_bat.update(bat_v, f"{prefix}_v_bat", render=is_active)

    def _apply_tile_visibility(self, active_keys):
        self.clear_widgets()
    
        from kivy.core.window import Window
    
        offset = dp_scaled(150)
        padding = dp_scaled(12)
        spacing = dp_scaled(12)
    
        available_height = max(0, Window.height - offset)
    
        num_tiles = len(active_keys)
    
        self.padding = [padding] * 4
        self.spacing = spacing
    
        # FIX: Grid stabil halten
        self.cols = 3
    
        # Anzahl Reihen dynamisch nur für Height-Berechnung
        rows = 1 if num_tiles <= 3 else 2
    
        usable_height = available_height - (padding * 2) - (spacing * (rows - 1))
        row_height = max(10, usable_height / rows)
    
        order = [
            "temp_in", "hum_in", "vpd_in",
            "temp_ex", "hum_ex", "vpd_ex",
            "leaf_temp", "vpd_leaf",
            "ble_temp_sps", "ble_hum_sps", "ble_vpd_sps",
            "ble_temp_tb2", "ble_hum_tb2", "ble_vpd_tb2",
            "circulation_fan_rpm", "exhaust_fan_rpm", "v_bat"
        ]
    
        for key in order:
            if key not in active_keys:
                continue
    
            tile = self.tile_map.get(key)
            if not tile:
                continue
    
            tile.size_hint_y = None
            tile.height = row_height
    
            self.add_widget(tile)