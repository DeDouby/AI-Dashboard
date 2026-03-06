# -*- coding: utf-8 -*-
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.togglebutton import ToggleButton
import os
import time
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Rectangle, Color, RoundedRectangle, Line
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from dashboard_gui.ui.common.control_buttons import ControlButtons

from dashboard_gui.global_state_manager import GLOBAL_STATE, ACTIVE_CHANNEL_ENGINE
from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.ui.i18n import I18N

class SensorMixedModeScreen(Screen):
    name = "sensor_mixed_mode"

    def __init__(self, **kw):
        super().__init__(**kw)
        self.GS = GLOBAL_STATE
        self.GS.ui_handler.attach_screen("sensor_mixed_mode", self)
        self._last_list_update = 0
        
        # 1. ROOT
        root = FloatLayout()
        self.add_widget(root)
        
        # Hintergrundbild
        with root.canvas.before:
            self.bg_rect = Rectangle(source=os.path.join("dashboard_gui", "assets", "background_mixed.png"))
        root.bind(pos=self._update_bg, size=self._update_bg)

        # 2. DER GRAPH (hinter dem UI)
        self.graph_widget = Widget()
        root.add_widget(self.graph_widget)

        # 3. MAIN_UI
        main_ui = BoxLayout(orientation="vertical")
        root.add_widget(main_ui)

        # --- HEADER ---
        self.header = HeaderBar()
        self.header.lbl_title.text = I18N.t("menu.sensor_mixed_mode")
        self.header.update_back_button("sensor_mixed_mode") 
        main_ui.add_widget(self.header)

        # --- CONTENT (Ohne Hintergrund-Box!) ---
        # Padding sorgt für Abstand zum Rand, damit die schwebenden Elemente nicht kleben
        content = BoxLayout(orientation="horizontal", padding=dp_scaled(15), spacing=dp_scaled(20), size_hint_y=1)
        main_ui.add_widget(content)

        # --- [LINKS: Scroll-Liste] ---
        self.left_col = BoxLayout(orientation="vertical", size_hint_x=0.45)
        self.lbl_details_title = Label(
            text="[b]Device Selector / Details[/b]",
            markup=True,
            font_size=sp_scaled(22),
            size_hint_y=None,
            height=dp_scaled(36),
            color=(1,1,1,0.85),
            halign="left",
            valign="middle"
        )
        self.lbl_details_title.bind(size=lambda s,w: setattr(s,"text_size",(w[0],None)))
        
        self.left_col.add_widget(self.lbl_details_title)
        self.scroll = ScrollView(do_scroll_x=False, bar_width=dp_scaled(2))
        self.details_list = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp_scaled(12))
        self.details_list.bind(minimum_height=self.details_list.setter("height"))
        self.scroll.add_widget(self.details_list)
        self.left_col.add_widget(self.scroll)
        content.add_widget(self.left_col)

        # --- [RECHTS: Durchschnittswerte in kompakter Box] ---
        self.right_col = BoxLayout(orientation="vertical", size_hint_x=0.55, padding=[0, dp_scaled(20)])
        
        # Die neue kompakte Box für die Averages
        self.avg_card = BoxLayout(
            orientation="vertical",
            padding=dp_scaled(18),
            spacing=dp_scaled(12),
            size_hint=(None, None),
            pos_hint={"center_x": 0.5}
        )
        
        self.avg_card.height = dp_scaled(300)
        self.avg_card.width  = dp_scaled(400)
        
        with self.avg_card.canvas.before:
            Color(0, 0, 0, 0.5) # Etwas dunkler für bessere Lesbarkeit der großen Zahlen
            self.avg_bg_rect = RoundedRectangle(radius=[dp_scaled(20)])
        self.avg_card.bind(pos=self._update_avg_rect, size=self._update_avg_rect)


        # ---- AVG TITLE ----
        self.lbl_avg_title = Label(
            text="[b]MIXED AVERAGES[/b]",
            markup=True,
            font_size=sp_scaled(22),
            size_hint_y=None,
            height=dp_scaled(36),
            color=(1,1,1,0.85),
            halign="center",
            valign="middle"
        )
        self.lbl_avg_title.bind(size=lambda s,w: setattr(s,"text_size",(w[0],None)))
        
        self.avg_card.add_widget(self.lbl_avg_title)

        self.lbl_temp = self._create_avg_label((1, 0.4, 0.4, 1))
        self.lbl_hum  = self._create_avg_label((0.4, 0.7, 1, 1))
        self.lbl_vpd  = self._create_avg_label((0.4, 1, 0.7, 1))
        self.lbl_dew  = self._create_avg_label((0.8, 0.8, 1, 1))
        
        for l in [self.lbl_temp, self.lbl_hum, self.lbl_vpd, self.lbl_dew]:
            self.avg_card.add_widget(l)
        
        # Spacer damit die Card oben schwebt oder zentriert ist
        self.right_col.add_widget(Widget(size_hint_y=0.2)) # Etwas Platz oben
        self.right_col.add_widget(self.avg_card)
        self.right_col.add_widget(Widget(size_hint_y=0.8)) # Drückt die Card nach oben/mitte
        
        content.add_widget(self.right_col)

        # --- CONTROL BUTTONS ---
        self.controls = ControlButtons()
        self.controls.size_hint = (1, None)
        self.controls.height = dp_scaled(40) # Schön griffig
        main_ui.add_widget(self.controls)

    def _create_avg_label(self, color):
        # Schriftgröße etwas angepasst für die Box
        return Label(text="--", font_size=sp_scaled(36), bold=True, markup=True, 
                     color=color, outline_width=1, outline_color=(0,0,0,1),
                     halign="center", valign="middle")

    def _update_avg_rect(self, instance, value):
        self.avg_bg_rect.pos = instance.pos
        self.avg_bg_rect.size = instance.size

    def _update_bg(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def _setup_columns(self, content):
        # LINKS: Scroll-Liste
        self.left_col = BoxLayout(orientation="vertical", size_hint_x=0.4)
        self.scroll = ScrollView(do_scroll_x=False)
        self.details_list = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp_scaled(12))
        self.details_list.bind(minimum_height=self.details_list.setter("height"))
        self.scroll.add_widget(self.details_list)
        self.left_col.add_widget(self.scroll)
        content.add_widget(self.left_col)

        # RECHTS: Durchschnittswerte
        self.right_col = BoxLayout(orientation="vertical", size_hint_x=0.6, padding=[dp_scaled(10), 0])
      
        self.lbl_temp = self._create_avg_label((1, 0.4, 0.4, 1))
        self.lbl_hum  = self._create_avg_label((0.4, 0.7, 1, 1))
        self.lbl_vpd  = self._create_avg_label((0.4, 1, 0.7, 1))
        self.lbl_dew  = self._create_avg_label((0.8, 0.8, 1, 1))
        
        for l in [self.lbl_temp, self.lbl_hum, self.lbl_vpd, self.lbl_dew]:
            self.avg_box.add_widget(l)
        self.right_col.add_widget(self.avg_box)
        content.add_widget(self.right_col)

    def _create_avg_label(self, color):
        return Label(text="--", font_size=sp_scaled(42), bold=True, markup=True, 
                     color=color, outline_width=1.5, outline_color=(0,0,0,1),
                     halign="center", valign="middle")


    def _update_bg(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def on_pre_enter(self):
        self.GS.mixed_mode_active = True
        self._update_details_list()

    def _toggle_dev(self, dev_id):
        if dev_id in self.GS.mixed_selected_buffers:
            self.GS.mixed_selected_buffers.remove(dev_id)
        else:
            self.GS.mixed_selected_buffers.add(dev_id)
            # Standard-Modus setzen falls nicht vorhanden
            if dev_id not in self.GS.mixed_device_modes:
                from dashboard_gui.data_buffer import BUFFER
                frame = next((f for f in (BUFFER.get() or []) if str(f.get("device_id")) == str(dev_id)), None)
                self.GS.mixed_device_modes[dev_id] = {"external"} if frame and self._has_external(frame) else {"internal"}
        
        self._update_details_list()
        self.draw_mixed_graph()

    def _switch_mode(self, dev_id, mode):
        modes = self.GS.mixed_device_modes.get(dev_id, {"internal"}).copy()
        if mode in modes:
            if len(modes) > 1: modes.remove(mode)
        else:
            modes.add(mode)
        self.GS.mixed_device_modes[dev_id] = modes
        self._update_details_list()

    def _update_details_list(self):
        """Baut die Liste der Geräte mit integrierter Steuerung auf."""
        self.details_list.clear_widgets()
        from dashboard_gui.data_buffer import BUFFER
        data = BUFFER.get() or []
        device_list = self.GS.get_device_list()

        for dev_id in device_list:
            is_selected = dev_id in self.GS.mixed_selected_buffers
            frame = next((f for f in data if str(f.get("device_id")) == str(dev_id)), None)
            
            # 1. Container für die gesamte Karte (Device + evtl. Modi)
            card_height = dp_scaled(110) if (is_selected and frame and self._has_external(frame)) else dp_scaled(75)
            card = BoxLayout(orientation="vertical", size_hint_y=None, height=card_height, spacing=dp_scaled(5))
            
            # 2. Der eigentliche Button-Bereich (als FloatLayout, damit wir schichten können)
            from kivy.uix.floatlayout import FloatLayout
            btn_area = FloatLayout(size_hint_y=1)
            
            # Der Background-Button (füllt die gesamte btn_area)
            btn_bg = ToggleButton(
                state="down" if is_selected else "normal",
                background_normal='', background_down='',
                background_color=(0, 0, 0, 0.35) if is_selected else (0, 0, 0, 0.2),
                size_hint=(1, 1), pos_hint={'x': 0, 'y': 0}
            )
            btn_bg.bind(on_release=lambda b, d=dev_id: self._toggle_dev(d))
            btn_area.add_widget(btn_bg)

            # Das Label-Layout (darüber liegend)
            content_overlay = BoxLayout(
                orientation="vertical", 
                padding=[dp_scaled(15), dp_scaled(10)],
                size_hint=(1, 1), pos_hint={'x': 0, 'y': 0}
            )
            
            name = ACTIVE_CHANNEL_ENGINE.get_device_label(dev_id)
            # Name in schönem Grün wenn aktiv
            name_color = "[color=#33ff99]" if is_selected else "[color=#ffffff]"
            lbl_name = Label(
                text=f"[font=FA]\uf2c7[/font]  [b]{name}[/b]",
                markup=True, font_size=sp_scaled(26), color=(0.2, 1, 0.6, 1),
                halign="left", valign="bottom", size_hint_y=0.5
            )
            lbl_name.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)))
            
            # Werte-String
            val_text = self._get_values_string(frame, dev_id) if frame else "Warte auf Daten..."
            lbl_vals = Label(
                text=val_text, font_size=sp_scaled(17), 
                color=(1, 1, 1, 0.8) if is_selected else (1, 1, 1, 0.4),
                halign="left", valign="top",
                size_hint_y=0.4
            )
            lbl_vals.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)))
            
            content_overlay.add_widget(lbl_name)
            content_overlay.add_widget(lbl_vals)
            
            btn_area.add_widget(content_overlay)
            card.add_widget(btn_area)

            # 3. SUB-MODI (Internal/External) - Falls vorhanden und ausgewählt
            if is_selected and frame and self._has_external(frame):
                mode_box = BoxLayout(size_hint_y=None, height=dp_scaled(35), spacing=dp_scaled(4))
                current_modes = self.GS.mixed_device_modes.get(dev_id, {"internal"})
                
                for m in ["internal", "external"]:
                    m_active = m in current_modes
                    m_btn = ToggleButton(
                        text=f"{'[font=FA]\uf015[/font]' if m=='internal' else '[font=FA]\uf0c2[/font]'} {m.upper()}",
                        markup=True, state="down" if m_active else "normal",
                        font_size=sp_scaled(11), bold=True,
                        background_normal='', background_down='',
                        background_color=(0, 0, 0, 0.7) if m_active else (0, 0, 0, 0.35),
                        color=(1, 1, 1, 1) if m_active else (1, 1, 1, 0.5)
                    )
                    m_btn.bind(on_release=lambda b, d=dev_id, mode=m: self._switch_mode(d, mode))
                    mode_box.add_widget(m_btn)
                card.add_widget(mode_box)

            # Trennlinie für die Optik
            with card.canvas.after:
                Color(1, 1, 1, 0.1)
                Line(points=[card.x, card.y, card.x + self.left_col.width, card.y], width=1)

            self.details_list.add_widget(card)

    def _get_values_string(self, frame, dev_id):
        """Berechnet die Durchschnittswerte für die Anzeige in der Liste."""
        active_modes = self.GS.mixed_device_modes.get(dev_id, {"internal"})
        t_vals, h_vals, v_vals, d_vals = [], [], [], []
        
        for ch_name in ("adv", "gatt"):
            ch = frame.get(ch_name, {})
            for m in active_modes:
                # Daten extrahieren
                m_data = ch.get(m, {})
                t = m_data.get("temperature", {}).get("value")
                h = m_data.get("humidity", {}).get("value")
                
                # VPD und Dew Point (hängen oft am Channel-Level oder Mode-Level)
                # Hier nutzen wir die Keys passend zu deinem System
                v = ch.get(f"vpd_{m}", {}).get("value")
                d = ch.get(f"dew_{m}", {}).get("value")
                
                if t is not None: t_vals.append(float(t))
                if h is not None: h_vals.append(float(h))
                if v is not None: v_vals.append(float(v))
                if d is not None: d_vals.append(float(d))
        
        if not t_vals and not h_vals:
            return "Warten auf Sensordaten..."

        # Einheiten holen
        u_t = self.GS.get_unit("mixed_avg_temp") or "°C"
        u_h = self.GS.get_unit("mixed_avg_hum") or "%"
        u_v = self.GS.get_unit("mixed_avg_vpd") or "kPa"
        u_d = self.GS.get_unit("mixed_avg_dew") or "°C"

        parts = []
        # Formatierung mit :.2f für zwei Nachkommastellen
        if t_vals:
            parts.append(f"T: {sum(t_vals)/len(t_vals):.2f}{u_t}")
        if h_vals:
            parts.append(f"H: {sum(h_vals)/len(h_vals):.2f}{u_h}")
        if v_vals:
            parts.append(f"V: {sum(v_vals)/len(v_vals):.2f}{u_v}")
        if d_vals:
            parts.append(f"D: {sum(d_vals)/len(d_vals):.2f}{u_d}")

        # Mit Trenner zusammenfügen
        return " | ".join(parts)

    def _has_external(self, frame):
        for ch in [frame.get("adv", {}), frame.get("gatt", {})]:
            if ch.get("external", {}).get("present"): return True
        return False

    def update_from_global(self, d):
        self.header.update_from_global(d)
        self.draw_mixed_graph()
        
        # Durchschnittswerte Rechts updaten
        names = {
            "temp": "Temperature",
            "hum": "Humidity",
            "vpd": "VPD",
            "dew": "Dew Point"
        }
        
        for key, label in [("temp", self.lbl_temp), ("hum", self.lbl_hum),
                           ("vpd", self.lbl_vpd), ("dew", self.lbl_dew)]:
            full_key = f"mixed_avg_{key}"
            val = self.GS.graph_engine.get_last_value(full_key)
            unit = self.GS.get_unit(full_key) or ""
            trend = self.GS.get_trend_icon(full_key) or ""
            
            title = names[key]  # Nur die normale Beschriftung
            
            if val is not None:
                label.text = f"[size={int(sp_scaled(18))}]{title}:[/size] {val:.2f}[size={int(sp_scaled(20))}]{unit} [font=FA]{trend}[/font][/size]"
            else:
                label.text = f"[size={int(sp_scaled(18))}]{title}:[/size] --"
    
        # Liste alle 3 Sek refreshen (Werte in der Liste)
        if time.time() - self._last_list_update > 3:
            self._update_details_list()
            self._last_list_update = time.time()

    def draw_mixed_graph(self):
        # Definition der Kurven
        curves = [
            ("mixed_avg_temp", (1, 0.4, 0.4, 0.9)), 
            ("mixed_avg_hum", (0.4, 0.7, 1, 0.8)), 
            ("mixed_avg_vpd", (0.4, 1, 0.7, 0.7))
        ]
        
        self.graph_widget.canvas.clear()
        
        with self.graph_widget.canvas:
            # Wir teilen die verfügbare Höhe durch die Anzahl der Kurven
            # Damit jede Kurve ihren eigenen "Platz" zum Atmen hat
            num_curves = len(curves)
            w, h = self.graph_widget.width, self.graph_widget.height
            x_off, y_off = self.graph_widget.x, self.graph_widget.y
            
            # Padding für den gesamten Widget-Bereich
            base_padding = h * 0.1
            available_h = h - (2 * base_padding)
            
            # Höhe pro Korridor
            section_h = available_h / num_curves

            for idx, (key, color) in enumerate(curves):
                points = self.GS.graph_engine.get_buffer(key)
                if not points or len(points) < 2: 
                    continue
                
                Color(*color)
                
                min_v, max_v = min(points), max(points)
                v_range = (max_v - min_v) if max_v > min_v else 1
                
                # Berechnung des vertikalen Offsets für diesen spezifischen Graphen
                # idx 0 (Temp) ist oben, idx 2 (VPD) ist unten
                # Wir lassen innerhalb der Sektion nochmal 10% Platz (inner_pad)
                inner_pad = section_h * 0.1
                current_section_y = y_off + base_padding + (num_curves - 1 - idx) * section_h
                
                line_pts = []
                for i, val in enumerate(points):
                    # X bleibt linear
                    px = x_off + (i / (len(points) - 1)) * w
                    
                    # Y wird innerhalb SEINER Sektion skaliert
                    normalized_val = (val - min_v) / v_range
                    py = current_section_y + inner_pad + (normalized_val * (section_h - 2 * inner_pad))
                    
                    line_pts.extend([px, py])
                
                # Zeichnen der Linie mit schönem Glow-Effekt (optional 2. Linie darunter)
                Line(points=line_pts, width=dp_scaled(2.2), joint='round', cap='round')
                
                # Optional: Ein ganz schwacher Schatten/Glow für die Tiefe
                Color(color[0], color[1], color[2], 0.15)
                Line(points=line_pts, width=dp_scaled(5), joint='round', cap='round')
    def reset_from_global(self):
        self.details_list.clear_widgets()