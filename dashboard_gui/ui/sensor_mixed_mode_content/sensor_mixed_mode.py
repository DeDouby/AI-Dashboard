# -*- coding: utf-8 -*-
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.togglebutton import ToggleButton
from kivy.clock import Clock
import os
from kivy.graphics import Rectangle, Color
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.ui.i18n import I18N
import math

class SensorMixedModeScreen(Screen):
    name = "sensor_mixed_mode"

    def __init__(self, **kw):
        super().__init__(**kw)
        ASSET_ROOT = os.path.join("dashboard_gui", "assets")
        self.GS = GLOBAL_STATE
        self.GS.attach_sensor_mixed_mode(self)
        self.device_modes = {}          # dev_id -> set("internal", "external")
        self.active_device_id = None    # aktuell ausgewähltes Gerät für Modus-Auswahl

        # ROOT
        root = BoxLayout(orientation="vertical", spacing=dp_scaled(10))
        self.add_widget(root)
        with root.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(
                source=os.path.join(ASSET_ROOT, "background_mixed.png"),
                pos=root.pos,
                size=root.size
            )
        root.bind(pos=lambda *_: setattr(self.bg_rect, "pos", root.pos),
                  size=lambda *_: setattr(self.bg_rect, "size", root.size))

        # HEADER
        self.header = HeaderBar()
        self.header.size_hint_y = None
        self.header.height = dp_scaled(48)
        self.header.lbl_title.text = I18N.t("menu.sensor_mixed_mode")
        self.header.update_back_button("sensor_mixed_mode")
        root.add_widget(self.header)

        # CENTER ZONE
        self.center_zone = BoxLayout(
            orientation="horizontal",
            padding=dp_scaled(15),
            spacing=dp_scaled(15),
            size_hint=(1, 1)
        )

        # LINKSSPALTE – DETAILS
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

        # RECHTSSPALTE – MITTELWERTE
        self.right_column = BoxLayout(
            orientation="vertical",
            size_hint_x=0.55,
            spacing=dp_scaled(12)
        )
        self.lbl_avg_temp = Label(text="--", font_size=sp_scaled(54), bold=True, markup=True)
        self.lbl_avg_hum  = Label(text="--", font_size=sp_scaled(50), color=(0.2,0.8,1,1), markup=True)
        self.lbl_avg_vpd  = Label(text="--", font_size=sp_scaled(48), color=(0.2,1,0.6,1), markup=True)
        self.right_column.add_widget(self.lbl_avg_temp)
        self.right_column.add_widget(self.lbl_avg_hum)
        self.right_column.add_widget(self.lbl_avg_vpd)

        self.center_zone.add_widget(self.left_column)
        self.center_zone.add_widget(self.right_column)
        root.add_widget(self.center_zone)

        # STATUS LABEL
        self.status_label = Label(
            text="",
            font_size=sp_scaled(20),
            color=(0.5,0.5,0.5,1),
            size_hint_y=None,
            height=dp_scaled(24)
        )
        root.add_widget(self.status_label)

        # DEVICE BUTTONS
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

    # ─────────────────────────────
    # DEVICE LIST
    # ─────────────────────────────
    def rebuild_device_list(self):
        self.device_box.clear_widgets()
        devices = self.GS.get_device_list() or []
        count = max(len(devices), 1)

        for dev_id in devices:
            device_slot = BoxLayout(orientation="vertical", spacing=dp_scaled(4), size_hint=(1/count, 1))

            # Gerät Button
            btn = ToggleButton(
                text=self.GS.get_device_label(dev_id),
                size_hint_y=None,
                height=dp_scaled(50),
                background_normal='',
                background_color=(0.15,0.15,0.18,1),
                color=(1,1,1,1),
                bold=True,
                state="down" if dev_id in self.GS.mixed_selected_buffers else "normal"
            )
            btn.bind(state=self._update_btn_color)
            btn.bind(on_press=lambda b, d=dev_id: self.select_device(d))
            device_slot.add_widget(btn)

            # Modus Buttons nur wenn aktiv ausgewählt
            data = self._get_latest_frame(dev_id)
            if dev_id == self.active_device_id and data and self._has_external(data):
                mode_box = BoxLayout(size_hint_y=None, height=dp_scaled(36), spacing=dp_scaled(4))
                for mode in ("internal", "external"):
                    tbtn = ToggleButton(
                        text=mode.capitalize(),
                        group=None,
                        state="down" if mode in self.device_modes.get(dev_id, {"internal"}) else "normal",
                        size_hint=(0.5, 1)
                    )
                    tbtn.bind(on_press=lambda b, d=dev_id, m=mode: self.toggle_device_mode(d, m, b.state))
                    mode_box.add_widget(tbtn)
                device_slot.add_widget(mode_box)

            self.device_box.add_widget(device_slot)

        self.update_values()

    def _update_btn_color(self, btn, state):
        btn.background_color = (0.12,0.20,0.45,1) if state=="down" else (0.15,0.15,0.18,1)

    # ─────────────────────────────
    # DEVICE SELECTION / MIXED MODE
    # ─────────────────────────────
    def select_device(self, dev_id):
        dev_id = str(dev_id)
        if dev_id in self.GS.mixed_selected_buffers:
            # Gerät ist aktiv → abwählen
            self.GS.mixed_selected_buffers.remove(dev_id)
            self.device_modes.pop(dev_id, None)
            if self.active_device_id == dev_id:
                self.active_device_id = None
        else:
            # Gerät ist nicht aktiv → auswählen
            self.GS.mixed_selected_buffers.add(dev_id)
            self.device_modes.setdefault(dev_id, {"internal"})
            self.active_device_id = dev_id
    
        self.rebuild_device_list()

    def toggle_mixed_device(self, dev_id):
        """Gerät für Mittelwertberechnung aktivieren/deaktivieren"""
        dev_id = str(dev_id)
        if dev_id in self.GS.mixed_selected_buffers:
            self.GS.mixed_selected_buffers.remove(dev_id)
            self.device_modes.pop(dev_id, None)
        else:
            self.GS.mixed_selected_buffers.add(dev_id)
            self.device_modes.setdefault(dev_id, {"internal"})

    def toggle_device_mode(self, dev_id, mode, state):
        """Internal/External Modus toggeln (mehrere gleichzeitig möglich)
           UND Gerät automatisch für Mixed aktivieren, falls noch nicht"""
        dev_id = str(dev_id)
        modes = self.device_modes.get(dev_id, set())
        if not isinstance(modes, set):
            modes = {modes}
    
        if state == "down":
            modes.add(mode)
            # Gerät automatisch für Mixed markieren
            if dev_id not in self.GS.mixed_selected_buffers:
                self.GS.mixed_selected_buffers.add(dev_id)
        else:
            modes.discard(mode)
    
        self.device_modes[dev_id] = modes if modes else {"internal"}
        self.update_values()

    # ─────────────────────────────
    # DATEN-HELPER
    # ─────────────────────────────
    def _get_latest_frame(self, dev_id):
        from dashboard_gui.data_buffer import BUFFER
        data = BUFFER.get() or []
        for frame in reversed(data):
            if str(frame.get("device_id")) == str(dev_id):
                return frame
        return None

    def _has_external(self, frame):
        for ch_name in ("adv", "gatt"):
            ch = frame.get(ch_name)
            if isinstance(ch, dict) and ch.get("external") and ch["external"].get("present"):
                return True
        return False

    def calc_vpd(self, temp, hum):
        """VPD in kPa berechnen aus Temp (°C) und Hum (%)"""
        es = 0.6108 * math.exp((17.27*temp)/(temp+237.3))
        ea = es * hum/100
        return es - ea

    # ─────────────────────────────
    # UPDATE VALUES
    # ─────────────────────────────
    def update_values(self):
        from dashboard_gui.data_buffer import BUFFER
    
        # Normierung Device ID
        def norm_id(dev):
            return str(dev.decode("utf-8")) if isinstance(dev, bytes) else str(dev)
    
        selected = {norm_id(x) for x in self.GS.mixed_selected_buffers}
        if not selected:
            self.lbl_avg_temp.text = "[color=ff3333]Kein Sensor aktiv[/color]"
            self.lbl_avg_hum.text = ""
            self.lbl_avg_vpd.text = ""
            self.details_label.text = "Wähle Sensoren unten aus"
            return
    
        data = BUFFER.get() or []
    
        sensor_values = {}
        averaging_map = {"temp": [], "hum": [], "vpd": []}
    
        for frame in data:
            dev_id = norm_id(frame.get("device_id"))
            if dev_id not in selected:
                continue
            sensor_values.setdefault(dev_id, {"temp": [], "hum": [], "vpd": []})
    
            active_modes = self.device_modes.get(dev_id, {"internal"})
            if not isinstance(active_modes, set):
                active_modes = {active_modes}
    
            for ch_name in ("adv", "gatt"):
                ch = frame.get(ch_name)
                if not isinstance(ch, dict):
                    continue
    
                for mode in active_modes:
                    vals = ch.get(mode)
                    if not isinstance(vals, dict):
                        continue
    
                    # Temperature
                    temp_obj = vals.get("temperature")
                    if temp_obj and temp_obj.get("value") is not None:
                        val = float(temp_obj["value"])
                        unit = temp_obj.get("unit", "°C")
                        sensor_values[dev_id]["temp"].append((val, unit))
                        averaging_map["temp"].append((val, unit))
    
                    # Humidity
                    hum_obj = vals.get("humidity")
                    if hum_obj and hum_obj.get("value") is not None:
                        val = float(hum_obj["value"])
                        sensor_values[dev_id]["hum"].append(val)
                        averaging_map["hum"].append(val)
    
                    # VPD – nur aus decoded lesen, LISTE füllen
                    vpd_key = "vpd_internal" if "internal" in active_modes else "vpd_external"
                    vpd_obj = ch.get(vpd_key)
                    
                    if isinstance(vpd_obj, dict) and vpd_obj.get("value") is not None:
                        val = float(vpd_obj["value"])
                        sensor_values[dev_id]["vpd"].append(val)
                        averaging_map["vpd"].append(val)
    
        # Details Text
        detail_lines = []
        for dev_id, vals in sensor_values.items():
            name = self.GS.get_device_label(dev_id)
            parts = []
            if vals["temp"]:
                # Anzeige: zuerst Unit vom ersten Sensorwert nehmen
                val, unit = vals["temp"][0]
                avg_val = sum(v for v, u in vals["temp"])/len(vals["temp"])
                parts.append(f"T: {avg_val:.1f}{unit}")
            if vals["hum"]:
                parts.append(f"H: {sum(vals['hum'])/len(vals['hum']):.1f}%")
            if vals["vpd"]:
                parts.append(f"V: {sum(vals['vpd'])/len(vals['vpd']):.2f} kPa")
            detail_lines.append(f"[b]{name}:[/b] {' | '.join(parts)}")
        self.details_label.text = "\n".join(detail_lines)
    
        # Durchschnittswerte
        if averaging_map["temp"]:
            val, unit = averaging_map["temp"][0]
            avg_val = sum(v for v, u in averaging_map["temp"])/len(averaging_map["temp"])
            self.lbl_avg_temp.text = f"{avg_val:.2f} {unit}"
        else:
            self.lbl_avg_temp.text = "-- °C"
    
        self.lbl_avg_hum.text = f"{sum(averaging_map['hum'])/len(averaging_map['hum']):.2f} %" if averaging_map['hum'] else "-- %"
        self.lbl_avg_vpd.text = f"{sum(averaging_map['vpd'])/len(averaging_map['vpd']):.2f} kPa" if averaging_map['vpd'] else "-- kPa"
    
        # Status
        self.status_label.text = f"Schnitt aus {len(sensor_values)} Geräten"

    # ─────────────────────────────
    # REFRESH / GLOBAL UPDATE
    # ─────────────────────────────
    def refresh_after_config(self):
        valid = set(self.GS.get_device_list())
        self.GS.mixed_selected_buffers &= valid
        self.rebuild_device_list()

    def on_pre_enter(self, *_):
        self.rebuild_device_list()

    def update_from_global(self, d):
        if hasattr(self, "header"):
            self.header.update_from_global(d)
        self.update_values()