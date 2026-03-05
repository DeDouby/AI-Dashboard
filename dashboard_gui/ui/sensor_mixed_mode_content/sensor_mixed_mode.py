# -*- coding: utf-8 -*-
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.togglebutton import ToggleButton
import os
from kivy.graphics import Rectangle, Color, Line
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.ui.i18n import I18N
from dashboard_gui.global_state_manager import ACTIVE_CHANNEL_ENGINE
from kivy.graphics import Color, RoundedRectangle, Line

import time

class SensorMixedModeScreen(Screen):
    name = "sensor_mixed_mode"

    def __init__(self, **kw):
        super().__init__(**kw)
        self.GS = GLOBAL_STATE
        self.GS.ui_handler.attach_screen("sensor_mixed_mode", self)
        
        # ROOT
        root = BoxLayout(orientation="vertical", spacing=dp_scaled(10))
        self.add_widget(root)
        with root.canvas.before:
            self.bg_rect = Rectangle(source=os.path.join("dashboard_gui", "assets", "background_mixed.png"))
        root.bind(pos=self._update_bg, size=self._update_bg)

        # HEADER
        self.header = HeaderBar()
        # HIER DIE KORREKTUR:
        self.header.lbl_title.text = I18N.t("menu.sensor_mixed_mode")
        self.header.update_back_button("sensor_mixed_mode") # Registriert den Screen
        root.add_widget(self.header)

        # MAIN CONTENT
        content = BoxLayout(orientation="horizontal", padding=dp_scaled(15), spacing=dp_scaled(15))
        
        # LINKS: Scroll-Liste für Einzelwerte
        self.left_col = BoxLayout(orientation="vertical", size_hint_x=0.45)
        self.scroll = ScrollView(do_scroll_x=False)
        self.details_list = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp_scaled(10))
        self.details_list.bind(minimum_height=self.details_list.setter("height"))
        self.scroll.add_widget(self.details_list)
        self.left_col.add_widget(self.scroll)

        # RECHTS: Große Anzeigen
# RECHTS: Die Spalte für die Durchschnittswerte
# RECHTS: Die Spalte für die Durchschnittswerte
        self.right_col = BoxLayout(orientation="vertical", size_hint_x=0.55, padding=dp_scaled(15))

        self.avg_box = BoxLayout(orientation="vertical", spacing=dp_scaled(5), padding=dp_scaled(20))

        with self.avg_box.canvas.before:
            Color(0, 0, 0, 0.45) 
            self.avg_bg_rect = RoundedRectangle(pos=self.avg_box.pos, size=self.avg_box.size, radius=[dp_scaled(15)])
        
        self.avg_box.bind(pos=self._update_avg_rect, size=self._update_avg_rect)

        # 1. Überschrift (Hardcoded)
        self.avg_title = Label(
            text="[b]Sensor Mix[/b]", markup=True, font_size=sp_scaled(22),
            size_hint_y=None, height=dp_scaled(40), color=(1, 1, 1, 0.8)
        )
        self.avg_box.add_widget(self.avg_title)

        # 2. Die Werte-Labels (jetzt mit Outlines und sanften Farben)
        # Wir nutzen kleinere Fonts für die Bezeichner direkt im Text-Update später
        self.lbl_temp = Label(text="--", font_size=sp_scaled(48), bold=True, markup=True, color=(1, 0.4, 0.4, 1), outline_width=1.5, outline_color=(0,0,0,1))
        self.lbl_hum  = Label(text="--", font_size=sp_scaled(48), bold=True, markup=True, color=(0.4, 0.7, 1, 1), outline_width=1.5, outline_color=(0,0,0,1))
        self.lbl_vpd  = Label(text="--", font_size=sp_scaled(48), bold=True, markup=True, color=(0.4, 1, 0.7, 1), outline_width=1.5, outline_color=(0,0,0,1))
        self.lbl_dew  = Label(text="--", font_size=sp_scaled(48), bold=True, markup=True, color=(0.8, 0.8, 1, 1), outline_width=1.5, outline_color=(0,0,0,1))
        
        for l in [self.lbl_temp, self.lbl_hum, self.lbl_vpd, self.lbl_dew]:
            l.halign = "center"
            l.valign = "middle"
            l.bind(size=lambda s, w: setattr(s, 'text_size', w)) 
            self.avg_box.add_widget(l)

        self.right_col.add_widget(self.avg_box)

        content.add_widget(self.left_col)
        content.add_widget(self.right_col)
        root.add_widget(content)

        # UNTEN: Selector
        self.device_box = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp_scaled(50), spacing=dp_scaled(5))
        root.add_widget(self.device_box)

    def _update_bg(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size
    def _update_avg_rect(self, instance, value):
        """Hält den schwarzen Hintergrund genau hinter der Box."""
        self.avg_bg_rect.pos = instance.pos
        self.avg_bg_rect.size = instance.size
    def on_pre_enter(self):
        self.GS.mixed_mode_active = True
        self.rebuild_selector()

    def rebuild_selector(self):
        self.device_box.clear_widgets()
        from dashboard_gui.data_buffer import BUFFER
        data_all = BUFFER.get() or []

        # Ermitteln, wie viele Geräte wir haben, um den Platz zu teilen
        device_list = self.GS.get_device_list()
        if not device_list:
            return

        for dev_id in device_list:
            is_selected = dev_id in self.GS.mixed_selected_buffers
            
            # --- DER FIX: size_hint_x=1 statt None/Width ---
            # Damit verteilt Kivy alle Container gleichmäßig über die gesamte Breite der device_box
            btn_container = BoxLayout(
                orientation="vertical", 
                spacing=dp_scaled(2), 
                size_hint_x=1  # <--- Nimmt sich seinen Anteil am Gesamtplatz
            )
            
            # --- HAUPTBUTTON (GERÄT) ---
            btn = ToggleButton(
                text=ACTIVE_CHANNEL_ENGINE.get_device_label(dev_id),
                state="down" if is_selected else "normal",
                markup=True,
                background_normal='', 
                background_down='',
                background_color=(0.0, 0.0, 0.0, 0.65) if is_selected else (0, 0, 0, 0.35),
                color=(1, 1, 1, 1) if is_selected else (1, 1, 1, 0.6),
                size_hint_y=1 if not is_selected else 0.6
            )
            btn.bind(on_release=lambda b, d=dev_id: self._toggle_dev(d))
            btn_container.add_widget(btn)

            # Modus-Buttons einblenden
            if is_selected:
                frame = next((f for f in data_all if str(f.get("device_id")) == str(dev_id)), None)
                if frame and self._has_external(frame):
                    mode_box = BoxLayout(spacing=dp_scaled(2), size_hint_y=0.4)
                    current_modes = self.GS.mixed_device_modes.get(dev_id, {"internal"})
                    
                    for m in ["internal", "external"]:
                        is_mode_active = m in current_modes
                        m_btn = ToggleButton(
                            text=f"{'[font=FA]\uf015[/font]' if m=='internal' else '[font=FA]\uf0c2[/font]'} {m[:3].upper()}",
                            markup=True, # Für die Icons
                            state="down" if is_mode_active else "normal",
                            font_size=sp_scaled(10),
                            bold=True,
                            background_normal='',
                            background_down='',
                            background_color=(0.0, 0.0, 0.0, 0.65) if is_mode_active else (0.0, 0.0, 0.0, 0.35),
                            color=(1, 1, 1, 1) if is_mode_active else (1, 1, 1, 0.5)
                        )
                        m_btn.bind(on_release=lambda b, d=dev_id, mode=m: self._switch_mode(d, mode))
                        mode_box.add_widget(m_btn)
                    
                    btn_container.add_widget(mode_box)

            self.device_box.add_widget(btn_container)

    def _switch_mode(self, dev_id, mode):
        modes = self.GS.mixed_device_modes.get(dev_id, {"internal"})
        if mode in modes and len(modes) > 1:
            modes.remove(mode)
        else:
            modes.add(mode)
        self.GS.mixed_device_modes[dev_id] = modes
        self.rebuild_selector()

    def _toggle_dev(self, dev_id):
    
        from dashboard_gui.data_buffer import BUFFER
        data_all = BUFFER.get() or []
    
        if dev_id in self.GS.mixed_selected_buffers:
    
            self.GS.mixed_selected_buffers.remove(dev_id)
    
            if dev_id in self.GS.mixed_device_modes:
                del self.GS.mixed_device_modes[dev_id]
    
        else:
    
            self.GS.mixed_selected_buffers.add(dev_id)
    
            # Frame suchen um external prüfen zu können
            frame = next((f for f in data_all if str(f.get("device_id")) == str(dev_id)), None)
    
            if frame and self._has_external(frame):
                self.GS.mixed_device_modes[dev_id] = {"external"}
            else:
                self.GS.mixed_device_modes[dev_id] = {"internal"}
    
        self.rebuild_selector()

    # Im MixedModeScreen
    def update_from_global(self, d):
        self.header.update_from_global(d)
        
        # Lokale Bezeichner für die Anzeige
        display_names = {
            "temp": "MIX TEMP",
            "hum":  "MIX HUM",
            "vpd":  "MIX VPD",
            "dew":  "MIX DEW"
        }

        def update_label(label_widget, suffix):
            full_key = f"mixed_avg_{suffix}"
            val = self.GS.graph_engine.get_last_value(full_key)
            unit = self.GS.get_unit(full_key) or ""
            trend = self.GS.get_trend_icon(full_key) or ""
            name = display_names.get(suffix, "")

            if val is not None:
                # [size=...] macht den Bezeichner und die Einheit etwas kleiner für den edlen Look
                # Trend-Pfeil steht jetzt ganz hinten
                label_widget.text = f"[size={int(sp_scaled(20))}]{name}:[/size] {val:.2f} [size={int(sp_scaled(24))}]{unit} [font=FA]{trend}[/font][/size]"
            else:
                label_widget.text = f"[size={int(sp_scaled(20))}]{name}:[/size] -- {unit}"

        # Updates triggern
        update_label(self.lbl_temp, "temp")
        update_label(self.lbl_hum,  "hum")
        update_label(self.lbl_vpd,  "vpd")
        update_label(self.lbl_dew,  "dew")

        # Details alle 2 Sek (Listen-Update)
        if not hasattr(self, "_last_list") or time.time() - self._last_list > 2:
            self._update_details()
            self._last_list = time.time()

    def _update_details(self):
        self.details_list.clear_widgets()
        from dashboard_gui.data_buffer import BUFFER
        
        data = BUFFER.get() or []
        selected = self.GS.mixed_selected_buffers
        
        # Wir sammeln die Daten pro Gerät (ähnlich der alten Logik)
        for frame in data:
            dev_id = str(frame.get("device_id"))
            if dev_id not in selected:
                continue

            name = ACTIVE_CHANNEL_ENGINE.get_device_label(dev_id)
            active_modes = self.GS.mixed_device_modes.get(dev_id, {"internal"})
            
            # Werte-Extraktion
            temp_list = []
            hum_list = []
            vpd_list = []

            for ch_name in ("adv", "gatt"):
                ch = frame.get(ch_name, {})
                for mode in active_modes:
                    m_data = ch.get(mode, {})
                    t = m_data.get("temperature", {}).get("value")
                    h = m_data.get("humidity", {}).get("value")
                    # VPD Key Logik (vpd_internal oder vpd_external)
                    v = ch.get(f"vpd_{mode}", {}).get("value")
                    
                    if t is not None: temp_list.append(float(t))
                    if h is not None: hum_list.append(float(h))
                    if v is not None: vpd_list.append(float(v))

            # UI Karte erstellen (85dp hoch wie im Original)
            dev_card = BoxLayout(orientation="vertical", size_hint_y=None, height=dp_scaled(85))
            
            # Zeile 1: Name mit Icon
            lbl_name = Label(
                text=f"[font=FA]\uf2c7[/font]  [b]{name}[/b]",
                markup=True, font_size=sp_scaled(26), color=(0.2, 1, 0.6, 1),
                halign="left", valign="bottom", size_hint_y=0.5
            )
            lbl_name.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)))
            
            # Zeile 2: Werte-String zusammenbauen
            parts = []
            
            temp_unit = self.GS.get_unit("mixed_avg_temp") or "°C"
            hum_unit = self.GS.get_unit("mixed_avg_hum") or "%"
            vpd_unit = self.GS.get_unit("mixed_avg_vpd") or "kPa"
            
            if temp_list:
                t = sum(temp_list) / len(temp_list)
                # ÄNDERUNG: von :.1f auf :.2f
                parts.append(f"T: {t:.2f}{temp_unit}")
            
            if hum_list:
                h = sum(hum_list) / len(hum_list)
                # ÄNDERUNG: von :.1f auf :.2f
                parts.append(f"H: {h:.2f}{hum_unit}")
            
            if vpd_list:
                v = sum(vpd_list) / len(vpd_list)
                # Bleibt :.2f (war schon so)
                parts.append(f"V: {v:.2f}{vpd_unit}")
            
            lbl_vals = Label(
                text=" | ".join(parts) if parts else "Warte auf Daten...",
                font_size=sp_scaled(24),
                color=(0.8, 0.8, 0.8, 1),
                halign="left",
                valign="top",
                size_hint_y=0.5
            )
            
            lbl_vals.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)))
            
            dev_card.add_widget(lbl_name)
            dev_card.add_widget(lbl_vals)

            # Trennlinie zeichnen (Canvas)
            with dev_card.canvas.after:
                Color(1, 1, 1, 0.15)
                Line(points=[dev_card.x, dev_card.y, 
                             dev_card.x + self.left_col.width * 0.9, dev_card.y], width=1)
            
            self.details_list.add_widget(dev_card)

    def _has_external(self, frame):
        """Prüft im Datenframe, ob ein externer Sensor vorhanden ist."""
        for ch_name in ("adv", "gatt"):
            ch = frame.get(ch_name)
            if isinstance(ch, dict) and ch.get("external") and ch["external"].get("present"):
                return True
        return False
    def reset_from_global(self):
        self.lbl_temp.text = "--"
        self.details_list.clear_widgets()