import os
from kivy.uix.gridlayout import GridLayout
from dashboard_gui.ui.dashboard_content.chart_tile import ChartTile
from dashboard_gui.ui.scaling_utils import dp_scaled
from dashboard_gui.global_state_manager import GLOBAL_STATE

from kivy.uix.scrollview import ScrollView

class DashboardMainPanel(GridLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.cols = 3
        self.spacing = dp_scaled(14) # minimal vergrößert für mehr Cleanliness
        self.padding = dp_scaled(14)
        self.size_hint_y = None
        self.bind(minimum_height=self.setter('height'))
        
        # Gedeckte, professionelle Farbwerte aus dem Design-Konzept (RGBA)
        c_temp = [0.95, 0.55, 0.22, 1]  # Matt-Bernstein
        c_hum  = [0.24, 0.56, 0.78, 1]  # Ruhiges Blau
        c_vpd  = [0.52, 0.38, 0.76, 1]  # Edles Violett
        c_green = [0.22, 0.68, 0.38, 1] # Smaragdgrün (Blatt/Fans)
        c_bat   = [0.85, 0.68, 0.15, 1] # Mattgelb

        # ---------------------------------------------------
        # TILES MIT NEUEM FARBSTIL INITIALISIEREN
        # ---------------------------------------------------
        self.tile_temp_in = ChartTile("temp_in", "Temperature Internal", "—", c_temp)
        self.tile_hum_in  = ChartTile("hum_in", "Humidity Internal", "%", c_hum)
        self.tile_vpd_in  = ChartTile("vpd_in", "VPD Internal", "kPa", c_vpd)
        
        self.tile_temp_ex = ChartTile("temp_ex", "Temperature External", "—", c_temp)
        self.tile_hum_ex  = ChartTile("hum_ex", "Humidity External", "%", c_hum)
        self.tile_vpd_ex  = ChartTile("vpd_ex", "VPD External", "kPa", c_vpd)
        
        self.tile_ble_temp_sps = ChartTile("ble_temp_sps", "Bluetooth SPS Temperature", "—", c_temp)
        self.tile_ble_hum_sps  = ChartTile("ble_hum_sps", "Bluetooth SPS Humidity", "%", c_hum)
        self.tile_ble_vpd_sps  = ChartTile("ble_vpd_sps", "Bluetooth SPS VPD", "kPa", c_vpd)
        
        self.tile_ble_temp_tb2 = ChartTile("ble_temp_tb2", "Bluetooth TB2 Temperature", "—", c_temp)
        self.tile_ble_hum_tb2  = ChartTile("ble_hum_tb2", "Bluetooth TB2 Humidity", "%", c_hum)
        self.tile_ble_vpd_tb2  = ChartTile("ble_vpd_tb2", "Bluetooth TB2 VPD", "kPa", c_vpd)
        
        self.tile_leaf_temp = ChartTile("leaf_temp", "Leaf Temperature", "—", c_green)
        self.tile_vpd_leaf  = ChartTile("vpd_leaf", "VPD Leaf", "kPa", c_vpd)
        
        self.tile_circulation_fan_rpm = ChartTile("circulation_fan_rpm", "Circulation Fan", "RPM", c_green)
        self.tile_exhaust_fan_rpm     = ChartTile("exhaust_fan_rpm", "Exhaust Fan", "RPM", c_green)
        
        self.tile_v_bat = ChartTile(
            "v_bat",
            "Battery",
            "V",
            c_bat
        )
        self.tile_map = {
            "temp_in": self.tile_temp_in, "hum_in": self.tile_hum_in, "vpd_in": self.tile_vpd_in,
            "temp_ex": self.tile_temp_ex, "hum_ex": self.tile_hum_ex, "vpd_ex": self.tile_vpd_ex,
            "leaf_temp": self.tile_leaf_temp, "vpd_leaf": self.tile_vpd_leaf, 
            "circulation_fan_rpm": self.tile_circulation_fan_rpm, "exhaust_fan_rpm": self.tile_exhaust_fan_rpm, 
            "v_bat": self.tile_v_bat,
            "ble_temp_sps": self.tile_ble_temp_sps, "ble_hum_sps":  self.tile_ble_hum_sps, "ble_vpd_sps":  self.tile_ble_vpd_sps,
            "ble_temp_tb2": self.tile_ble_temp_tb2, "ble_hum_tb2":  self.tile_ble_hum_tb2, "ble_vpd_tb2":  self.tile_ble_vpd_tb2 
        }
        
    # (update_from_data & _apply_tile_visibility bleiben logisch intakt wie vorher)



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
    
        offset = dp_scaled(100)
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
            "ble_temp_sps", "ble_hum_sps", "ble_vpd_sps",
            "ble_temp_tb2", "ble_hum_tb2", "ble_vpd_tb2",
            "leaf_temp", "vpd_leaf",

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