# -*- coding: utf-8 -*-
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.togglebutton import ToggleButton
from kivy.clock import Clock

from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.ui.i18n import I18N

class SensorMixedModeScreen(Screen):
    name = "sensor_mixed_mode"

    def __init__(self, **kw):
        super().__init__(**kw)
        self.GS = GLOBAL_STATE
        self.GS.attach_sensor_mixed_mode(self)
    
        # ROOT
        root = BoxLayout(orientation="vertical", spacing=dp_scaled(10))
        self.add_widget(root)
    
        # HEADER
        self.header = HeaderBar()
        self.header.size_hint_y = None
        self.header.height = dp_scaled(48)
        self.header.lbl_title.text = I18N.t("menu.sensor_mixed_mode")
        self.header.update_back_button("sensor_mixed_mode")
        root.add_widget(self.header)
    
        # CENTER ZONE (ZWEISPALTIG)
        self.center_zone = BoxLayout(
            orientation="horizontal",
            padding=dp_scaled(15),
            spacing=dp_scaled(15),
            size_hint=(1, 1)
        )
    
        # ─────────────────────────────
        # LINKSSPALTE – SENSOR DETAILS
        # ─────────────────────────────
        self.left_column = BoxLayout(
            orientation="vertical",
            size_hint_x=0.45,
            spacing=dp_scaled(10)
        )
    
        self.details_label = Label(
            text="",
            font_size=sp_scaled(22),
            color=(0.8, 0.8, 0.8, 1),
            halign="left",
            valign="top",
            markup=True
        )
        self.details_label.bind(size=self.details_label.setter("text_size"))
    
        self.left_column.add_widget(self.details_label)
    
        # ─────────────────────────────
        # RECHTSSPALTE – MITTELWERTE
        # ─────────────────────────────
        self.right_column = BoxLayout(
            orientation="vertical",
            size_hint_x=0.55,
            spacing=dp_scaled(12)
        )
    
        self.lbl_avg_temp = Label(
            text="--",
            font_size=sp_scaled(54),
            bold=True,
            markup=True
        )
    
        self.lbl_avg_hum = Label(
            text="--",
            font_size=sp_scaled(50),
            color=(0.2, 0.8, 1, 1),
            markup=True
        )
    
        self.lbl_avg_vpd = Label(
            text="--",
            font_size=sp_scaled(48),
            color=(0.2, 1, 0.6, 1),
            markup=True
        )
    
        self.right_column.add_widget(self.lbl_avg_temp)
        self.right_column.add_widget(self.lbl_avg_hum)
        self.right_column.add_widget(self.lbl_avg_vpd)
    
        # CENTER ZUSAMMENSETZEN
        self.center_zone.add_widget(self.left_column)
        self.center_zone.add_widget(self.right_column)
    
        # STATUS (UNTEN, ÜBER GANZE BREITE)
        self.status_label = Label(
            text="",
            font_size=sp_scaled(20),
            color=(0.5, 0.5, 0.5, 1),
            size_hint_y=None,
            height=dp_scaled(24)
        )
    
        root.add_widget(self.center_zone)
        root.add_widget(self.status_label)

        # DEVICE BUTTONS CONTAINER
        self.device_box = BoxLayout(
            orientation="horizontal",
            spacing=dp_scaled(8),
            size_hint_y=None,
            height=dp_scaled(48),
            padding=(dp_scaled(10), dp_scaled(5))
        )
        root.add_widget(self.device_box)

        self.GS.set_mixed_mode(True)
        self.rebuild_device_list()

        Clock.schedule_interval(lambda dt: self.update_values(), 0.5)

    def rebuild_device_list(self):
        self.device_box.clear_widgets()
        devices = self.GS.get_device_list() or []
        count = max(len(devices), 1)
        
        for dev_id in devices:
            btn = ToggleButton(
                text=self.GS.get_device_label(dev_id),
                size_hint=(1 / count, 1),
                height=dp_scaled(50),
                # SCHÖNERES DESIGN: Dunkles Anthrazit, Text weiß
                background_normal='',
                background_color=(0.15, 0.15, 0.18, 1), 
                color=(1, 1, 1, 1),
                bold=True,
                state="down" if dev_id in self.GS.mixed_selected_buffers else "normal"
            )
            # Logik für "Aktiv-Farbe" (Blau wenn ausgewählt)
            btn.bind(state=self._update_btn_color)
            if btn.state == 'down':
                btn.background_color = (0.2, 0.4, 0.8, 1)

            btn.bind(on_press=lambda b, d=dev_id: self.toggle_device(d))
            self.device_box.add_widget(btn)
        self.update_values()

    def _update_btn_color(self, btn, state):
        if state == 'down':
            btn.background_color = (0.12, 0.20, 0.45, 1) # Aktiv-Blau
        else:
            btn.background_color = (0.15, 0.15, 0.18, 1) # Dunkel-Grau

    def toggle_device(self, dev_id):
        dev_id = str(dev_id)
        if dev_id in self.GS.mixed_selected_buffers:
            self.GS.mixed_selected_buffers.remove(dev_id)
        else:
            self.GS.mixed_selected_buffers.add(dev_id)
        self.update_values()

    def update_values(self):
        def norm_id(dev):
            return str(dev.decode("utf-8")) if isinstance(dev, bytes) else str(dev)
    
        selected = {norm_id(x) for x in self.GS.mixed_selected_buffers}
        if not selected:
            self.lbl_avg_temp.text = "[color=ff3333]Kein Sensor aktiv[/color]"
            self.lbl_avg_hum.text = ""
            self.lbl_avg_vpd.text = ""
            self.details_label.text = "Wähle Sensoren unten aus"
            return
    
        from dashboard_gui.data_buffer import BUFFER
        data = BUFFER.get() or []
    
        sensor_values = {} 
        averaging_map = {"temp": [], "hum": [], "vpd": []}
    
        for frame in data:
            dev_id = norm_id(frame.get("device_id"))
            if dev_id not in selected: continue
            
            if dev_id not in sensor_values:
                sensor_values[dev_id] = {}

            for ch_name in ("adv", "gatt"):
                ch = frame.get(ch_name)
                if not isinstance(ch, dict): continue

                # VPD Check (GSM Pfade)
                for v_key in ("vpd_internal", "vpd_external"):
                    v_data = ch.get(v_key)
                    if isinstance(v_data, dict) and v_data.get("value") is not None:
                        val = float(v_data["value"])
                        sensor_values[dev_id]["vpd"] = val

                # Temp/Hum/VPD Pfade (internal/external)
                for src in ("internal", "external"):
                    vals = ch.get(src, {})
                    if not isinstance(vals, dict): continue
                    
                    for key, obj in vals.items():
                        if isinstance(obj, dict) and obj.get("value") is not None:
                            val = float(obj["value"])
                            k_low = key.lower()
                            if "temp" in k_low: sensor_values[dev_id]["temp"] = val
                            elif "hum" in k_low: sensor_values[dev_id]["hum"] = val
                            elif "vpd" in k_low: sensor_values[dev_id]["vpd"] = val

        # Sammeln für Durchschnitt
        for dev_id, vals in sensor_values.items():
            for k in averaging_map.keys():
                if k in vals:
                    averaging_map[k].append(vals[k])

        # 1. Details Text
        detail_lines = []
        for dev_id, vals in sensor_values.items():
            name = self.GS.get_device_label(dev_id)
            parts = []
            if "temp" in vals: parts.append(f"T: {vals['temp']:.1f}°")
            if "hum" in vals: parts.append(f"H: {vals['hum']:.1f}%")
            if "vpd" in vals: parts.append(f"V: {vals['vpd']:.2f}")
            detail_lines.append(f"[b]{name}:[/b] {' | '.join(parts)}")
        self.details_label.text = "\n".join(detail_lines)

        # 2. Mittelwerte anzeigen
        def calc_and_display(label, key, unit):
            v_list = averaging_map[key]
            if v_list:
                avg = sum(v_list) / len(v_list)
                label.text = f"{avg:.2f} {unit}"
            else:
                label.text = f"-- {unit}"

        calc_and_display(self.lbl_avg_temp, "temp", "°C")
        calc_and_display(self.lbl_avg_hum, "hum", "%")
        calc_and_display(self.lbl_avg_vpd, "vpd", "kPa")

        self.status_label.text = f"Schnitt aus {len(sensor_values)} Geräten"

    def update_from_global(self, d):
        if hasattr(self, "header"):
            self.header.update_from_global(d)
        self.update_values()