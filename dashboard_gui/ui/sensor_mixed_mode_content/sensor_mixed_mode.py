# -*- coding: utf-8 -*-
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.togglebutton import ToggleButton
from kivy.clock import Clock
import os
from kivy.graphics import Rectangle, Color
from kivy.uix.widget import Widget
from kivy.graphics import Rectangle, Color, Line
from kivy.uix.scrollview import ScrollView
import config
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.ui.i18n import I18N
from datetime import datetime
import math
import json
class SensorMixedModeScreen(Screen):
    name = "sensor_mixed_mode"

    def __init__(self, **kw):
        super().__init__(**kw)
        ASSET_ROOT = os.path.join("dashboard_gui", "assets")
        self.GS = GLOBAL_STATE
        self.GS.attach_sensor_mixed_mode(self)
        self.device_modes = {}          # dev_id -> set("internal", "external")
        # Trend Buffer für gemittelte Werte
        self._trend_buf = {
            "temp": [],
            "hum": [],
            "vpd": [],
            "dew": [],
        }
        self._trend_window = 120 
        self.active_device_id = None    # aktuell ausgewähltes Gerät für Modus-Auswahl
        # Avg-Temp Hintergrundgraph
        self._avg_graph_temp = []
        self._avg_graph_len = 60
         
        self._trend_window = config.get_tile_graph_window()

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

        # LINKSSPALTE – DETAILS (Jetzt mit ScrollView)
        self.left_column = BoxLayout(
            orientation="vertical",
            size_hint_x=0.45,
            spacing=dp_scaled(10)
        )
        
        # ScrollView für die Sensor-Details
        self.details_scroll = ScrollView(do_scroll_x=False, bar_width=dp_scaled(4))
        self.details_list_body = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp_scaled(12),
            padding=[dp_scaled(5), dp_scaled(5)]
        )
        # Wichtig: Damit die ScrollView weiß, wie hoch der Inhalt ist
        self.details_list_body.bind(minimum_height=self.details_list_body.setter("height"))
        
        self.details_scroll.add_widget(self.details_list_body)
        self.left_column.add_widget(self.details_scroll)

        # RECHTSSPALTE – MITTELWERTE
        self.right_column = BoxLayout(
            orientation="vertical",
            size_hint_x=0.55,
            spacing=dp_scaled(12)
        )
        self.lbl_avg_temp = Label(text="--", font_size=sp_scaled(54), color=(1,0,0,1), bold=True, markup=True)
        self.lbl_avg_hum  = Label(text="--", font_size=sp_scaled(54), color=(0.2, 0.6, 1, 1), bold=True, markup=True)
        self.lbl_avg_vpd  = Label(text="--", font_size=sp_scaled(54), color=(0.2,1,0.6,1), bold=True, markup=True)
        self.lbl_avg_dew  = Label(
            text="--",
            font_size=sp_scaled(54),
            color=(0.7,0.7,0.9,1),
            bold=True,
            markup=True
        )
        self.right_column.add_widget(self.lbl_avg_temp)
        self.right_column.add_widget(self.lbl_avg_hum)
        self.right_column.add_widget(self.lbl_avg_vpd)
        self.right_column.add_widget(self.lbl_avg_dew)   # 🔥 NEU

        self.center_zone.add_widget(self.left_column)
        self.center_zone.add_widget(self.right_column)
        root.add_widget(self.center_zone)

        # STATUS LABEL
        self.status_label = Label(
            text="",
            font_size=sp_scaled(26),
            color=(0.2,1,0.6,1),
            size_hint_y=None,
            height=dp_scaled(24)
        )
        root.add_widget(self.status_label)
        
        self.avg_graph_widget = Widget(size_hint=(1, None), height=dp_scaled(60))
        self.right_column.add_widget(self.avg_graph_widget, index=0)  # hinter Labels

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
                active_modes = self.device_modes.get(dev_id, {"internal"})
                if not isinstance(active_modes, set):
                    active_modes = {active_modes}
    
                for mode in ("internal", "external"):
                    tbtn = ToggleButton(
                        text=mode.capitalize(),
                        group=None,
                        state="down" if mode in active_modes else "normal",
                        size_hint=(0.5, 1)
                    )
    
                    # Klick-Handler sorgt jetzt für min. 1 Modus
                    def on_mode_toggle(b, d=dev_id, m=mode):
                        modes = self.device_modes.get(d, {"internal"})
                        if not isinstance(modes, set):
                            modes = {modes}
                        if b.state == "down":
                            modes.add(m)
                            self.GS.mixed_selected_buffers.add(d)
                        else:
                            if len(modes) == 1 and m in modes:
                                # ❌ Minimum 1 Modus bleibt aktiv
                                b.state = "down"
                                return
                            modes.discard(m)
                        self.device_modes[d] = modes
                        self.update_values()
                        # UI sofort syncen
                        self.rebuild_device_list()
    
                    tbtn.bind(on_press=on_mode_toggle)
                    mode_box.add_widget(tbtn)
    
                device_slot.add_widget(mode_box)
    
            self.device_box.add_widget(device_slot)
    
        self.update_values()

    def _update_btn_color(self, btn, state):
        btn.background_color = (0.12,0.20,0.45,1) if state=="down" else (0.15,0.15,0.18,1)

    def _calc_trend_arrow(self, key, value):
        buf = self._trend_buf[key]
        buf.append(value)
        if len(buf) > self._trend_window:
            buf.pop(0)

        if len(buf) < 3:
            return ""

        start = buf[0]
        end = buf[-1]
        diff = end - start

        threshold = max(0.01, abs(start) * 0.002)

        if diff > threshold:
            return "[font=FA]\uf062[/font]"   # arrow-up
        elif diff < -threshold:
            return "[font=FA]\uf063[/font]"   # arrow-down
        else:
            return "[font=FA]\uf061[/font]"   # arrow-right

    def _draw_avg_temp_bg(self, *_):
        if not self._avg_graph_temp or len(self._avg_graph_temp) < 2:
            return
    
        # Größe aktuell holen
        w, h = self.avg_graph_widget.width, self.avg_graph_widget.height
        if w == 0 or h == 0:
            # noch nicht laid out → wieder versuchen später
            Clock.schedule_once(self._draw_avg_temp_bg, 0.1)
            return
    
        buf = self._avg_graph_temp
        vmin = min(buf)
        vmax = max(buf)
        span = max(vmax - vmin, 0.0001)
        step_x = w / (len(buf) - 1)
        points = []
    
        for i, v in enumerate(buf):
            x = i * step_x
            y = (v - vmin) / span * h
            points.extend([x, y])
    
        self.avg_graph_widget.canvas.before.clear()
        with self.avg_graph_widget.canvas.before:
            Color(1, 1, 1, 0.06)
            Line(points=points, width=1)
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
        """Internal/External Modus toggeln (mindestens eins muss aktiv sein)"""
        dev_id = str(dev_id)
        modes = self.device_modes.get(dev_id, {"internal"})
        if not isinstance(modes, set):
            modes = {modes}
    
        if state == "down":
            modes.add(mode)
            # Gerät automatisch für Mixed markieren
            self.GS.mixed_selected_buffers.add(dev_id)
        else:
            if len(modes) == 1 and mode in modes:
                # ❌ Minimum 1 Modus bleibt aktiv → nicht entfernen
                pass  # nichts tun
            else:
                modes.discard(mode)
    
        self.device_modes[dev_id] = modes
    
        # 🔹 UI sofort korrigieren: Buttons anpassen
        self.rebuild_device_list()  # dadurch werden Buttons korrekt gesetzt
    
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
        import core
    
        # 1. Auswahl validieren
        def norm_id(dev):
            return str(dev.decode("utf-8")) if isinstance(dev, bytes) else str(dev)
    
        selected = {norm_id(x) for x in self.GS.mixed_selected_buffers}
        
        # --- SOFORT-STOPP WENN NICHTS GEWÄHLT ---
        if not selected:
            self.lbl_avg_temp.text = "[color=ff3333]Kein Sensor aktiv[/color]"
            self.lbl_avg_hum.text = ""
            self.lbl_avg_vpd.text = ""
            self.lbl_avg_dew.text = ""
            self.status_label.text = "Schnitt aus 0 Geräten" # Direkt auf 0 setzen
            self.details_list_body.clear_widgets()
            
            # mixed.json sofort leeren
            try:
                mixed_path = os.path.join("data", "mixed.json")
                with open(mixed_path, "w", encoding="utf-8") as f:
                    json.dump([], f)
            except:
                pass
            return 
        # ----------------------------------------

        data = BUFFER.get() or []
        sensor_values = {}
        averaging_map = {"temp": [], "hum": [], "vpd": [], "dew": []}
    
        for frame in data:
            dev_id = norm_id(frame.get("device_id"))
            if dev_id not in selected:
                continue
            
            # Initialisiere Gerät in der Map, falls noch nicht geschehen
            if dev_id not in sensor_values:
                sensor_values[dev_id] = {"temp": [], "hum": [], "vpd": [], "dew": []}
            
            active_modes = self.device_modes.get(dev_id, {"internal"})
            if not isinstance(active_modes, set):
                active_modes = {active_modes}
    
            for ch_name in ("adv", "gatt"):
                ch = frame.get(ch_name)
                if not isinstance(ch, dict): continue
    
                for mode in active_modes:
                    vals = ch.get(mode)
                    if not isinstance(vals, dict): continue
    
                    # Temperature
                    temp_obj = vals.get("temperature")
                    if temp_obj and temp_obj.get("value") is not None:
                        v, u = float(temp_obj["value"]), temp_obj.get("unit", "°C")
                        sensor_values[dev_id]["temp"].append((v, u))
                        averaging_map["temp"].append((v, u))
    
                    # Humidity
                    hum_obj = vals.get("humidity")
                    if hum_obj and hum_obj.get("value") is not None:
                        v = float(hum_obj["value"])
                        sensor_values[dev_id]["hum"].append(v)
                        averaging_map["hum"].append(v)

                    # Dew Point
                    dp_key = "dew_point_internal" if mode == "internal" else "dew_point_external"
                    dp_obj = ch.get(dp_key)
                    if isinstance(dp_obj, dict) and dp_obj.get("value") is not None:
                        v, u = float(dp_obj["value"]), dp_obj.get("unit", "°C")
                        sensor_values[dev_id]["dew"].append((v, u))
                        averaging_map["dew"].append((v, u))

                    # VPD
                    vpd_key = "vpd_internal" if mode == "internal" else "vpd_external"
                    vpd_obj = ch.get(vpd_key)
                    if isinstance(vpd_obj, dict) and vpd_obj.get("value") is not None:
                        v = float(vpd_obj["value"])
                        sensor_values[dev_id]["vpd"].append(v)
                        averaging_map["vpd"].append(v)
    
        # Details UI Update
        self.details_list_body.clear_widgets()
        self.details_list_body.spacing = dp_scaled(20) 

        for dev_id, vals in sensor_values.items():
            name = self.GS.get_device_label(dev_id)
            dev_card = BoxLayout(orientation="vertical", size_hint_y=None, height=dp_scaled(85))
            
            lbl_name = Label(
                text=f"[font=FA]\uf2c7[/font]  [b]{name}[/b]",
                markup=True, font_size=sp_scaled(26), color=(0.2, 1, 0.6, 1),
                halign="left", valign="bottom", size_hint_y=0.5
            )
            lbl_name.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)))
            
            parts = []
            if vals["temp"]:
                avg_t = sum(x[0] for x in vals["temp"])/len(vals["temp"])
                parts.append(f"T: {avg_t:.1f}°C")
            if vals["hum"]:
                parts.append(f"H: {sum(vals['hum'])/len(vals['hum']):.1f}%")
            if vals["vpd"]:
                parts.append(f"V: {sum(vals['vpd'])/len(vals['vpd']):.2f}kPa")
            
            lbl_vals = Label(
                text=" | ".join(parts), font_size=sp_scaled(24),
                color=(0.8, 0.8, 0.8, 1), halign="left", valign="top", size_hint_y=0.5
            )
            lbl_vals.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)))
            
            dev_card.add_widget(lbl_name)
            dev_card.add_widget(lbl_vals)

            with dev_card.canvas.after:
                Color(1, 1, 1, 0.15)
                Line(points=[dev_card.x, dev_card.y - dp_scaled(10), 
                             dev_card.x + self.left_column.width * 0.9, dev_card.y - dp_scaled(10)], width=1)
            self.details_list_body.add_widget(dev_card)

        # Durchschnittswerte & Trends
        avg_temp_val = None
        if averaging_map["temp"]:
            avg_temp_val = sum(x[0] for x in averaging_map["temp"]) / len(averaging_map["temp"])
            self.lbl_avg_temp.text = f"{self._calc_trend_arrow('temp', avg_temp_val)} {avg_temp_val:.2f} °C"
            self._avg_graph_temp.append(avg_temp_val)
            if len(self._avg_graph_temp) > self._avg_graph_len: self._avg_graph_temp.pop(0)
        else:
            self.lbl_avg_temp.text = "-- °C"
        
        if averaging_map["hum"]:
            avg_hum_val = sum(averaging_map["hum"]) / len(averaging_map["hum"])
            self.lbl_avg_hum.text = f"{self._calc_trend_arrow('hum', avg_hum_val)} {avg_hum_val:.2f} %"
        else:
            avg_hum_val = None
            self.lbl_avg_hum.text = "-- %"

        if averaging_map["vpd"]:
            avg_vpd_val = sum(averaging_map["vpd"]) / len(averaging_map["vpd"])
            self.lbl_avg_vpd.text = f"{self._calc_trend_arrow('vpd', avg_vpd_val)} {avg_vpd_val:.2f} kPa"
        else:
            avg_vpd_val = None
            self.lbl_avg_vpd.text = "-- kPa"

        if averaging_map["dew"]:
            avg_dew_val = sum(x[0] for x in averaging_map["dew"]) / len(averaging_map["dew"])
            self.lbl_avg_dew.text = f"{self._calc_trend_arrow('dew', avg_dew_val)} {avg_dew_val:.2f} °C"
        else:
            avg_dew_val = None
            self.lbl_avg_dew.text = "-- °C"

        # mixed.json Update
        mixed_path = os.path.join("data", "mixed.json")
        try:
            if sensor_values and avg_temp_val is not None:
                json_data = [{
                    "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
                    "name": "MixedSensor", "address": "MIXED-AVG", "note": "mixed",
                    "avg_temp": avg_temp_val, "avg_hum": avg_hum_val,
                    "avg_vpd": avg_vpd_val, "avg_dew": avg_dew_val,
                    "devices": list(sensor_values.keys())
                }]
                with open(mixed_path, "w", encoding="utf-8") as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
            else:
                with open(mixed_path, "w", encoding="utf-8") as f:
                    json.dump([], f)
        except:
            pass

        # Hier ist die Korrektur für das Status Label: 
        # Es zählt nur die Geräte, die wirklich DATEN geliefert haben UND selektiert sind.
        self.status_label.text = f"Schnitt aus {len(sensor_values)} Geräten"
        self._draw_avg_temp_bg()

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
        self.header._last_frame = d
        self.update_values()