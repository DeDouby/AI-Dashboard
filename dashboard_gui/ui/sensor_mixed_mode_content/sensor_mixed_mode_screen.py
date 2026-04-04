# -*- coding: utf-8 -*-
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Rectangle, Color, Line
from kivy.uix.widget import Widget
import os
import config
from kivy.uix.boxlayout import BoxLayout  # <-- DIESER HAT GEFEHLT
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.common.control_buttons import ControlButtons
from dashboard_gui.ui.sensor_mixed_mode_content.mixed_mode_data_handler import MixedModeDataHandler
from dashboard_gui.ui.sensor_mixed_mode_content.mixed_mode_panel import MixedModePanel
from kivy.metrics import dp
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled

class SensorMixedModeScreen(Screen):
    name = "sensor_mixed_mode"

    def __init__(self, **kw):
        super().__init__(**kw)
        self.GS = GLOBAL_STATE
        self.GS.ui_handler.attach_screen(self.name, self)
        
        root = FloatLayout()
        self.add_widget(root)

        # Hintergrund
        with root.canvas.before:
            self.bg_rect = Rectangle(source=os.path.join("dashboard_gui", "assets", "background_mixed.png"))
        root.bind(size=self._update_bg)

        # Graph Widget (Hintergrund)
        self.graph_widget = Widget()
        root.add_widget(self.graph_widget)

        # UI Layout
        layout = BoxLayout(orientation="vertical")
        self.header = HeaderBar()
        layout.add_widget(self.header)
        self.header.lbl_title.text = "Mixed-Mode"
        self.header.update_back_button("setup")
        self.panel = MixedModePanel(self)
        layout.add_widget(self.panel)

        self.controls = ControlButtons()
        self.controls.size_hint = (1,None)
        self.controls.height = dp_scaled(40)
        self.controls.pos_hint = {'y':0}
        layout.add_widget(self.controls)
        root.add_widget(layout)

        self.handler = MixedModeDataHandler(self)

    def _update_bg(self, *args):
        self.bg_rect.size = self.size

    def on_pre_enter(self):
        self.GS.mixed_mode_active = True
        self.handler.refresh()

    def _toggle_dev(self, dev_id):
        # 1. RAM Update
        if dev_id in self.GS.mixed_selected_buffers:
            self.GS.mixed_selected_buffers.remove(dev_id)
            # NEU: Speichern in config.json
            config.set_mixed_enabled(dev_id, False) 
        else:
            self.GS.mixed_selected_buffers.add(dev_id)
            # NEU: Speichern in config.json
            config.set_mixed_enabled(dev_id, True)
            # Sicherstellen, dass ein Modus existiert, falls noch nie gesetzt
            if dev_id not in self.GS.mixed_device_modes:
                self.GS.mixed_device_modes[dev_id] = {"internal"}
                config.set_mixed_external(dev_id, False)

        self.handler.refresh()

    def _switch_mode(self, dev_id, mode):
        modes = self.GS.mixed_device_modes.get(dev_id, {"internal"}).copy()
        
        # Mode Toggle Logik
        if mode in modes:
            if len(modes) > 1: 
                modes.remove(mode)
        else:
            modes.add(mode)
        
        # 1. RAM Update
        self.GS.mixed_device_modes[dev_id] = modes
        
        # 2. NEU: Speichern in config.json
        # Wir prüfen einfach, ob "external" im Set ist
        is_external = "external" in modes
        config.set_mixed_external(dev_id, is_external)
        
        self.handler.refresh()

    def update_from_global(self, d):
        self.header.update_from_global(d)
        # HIER DIE ARCHITEKTUR-ÄNDERUNG:
        self.handler.update_live_data() # Nur Werte schieben, nicht Liste killen
        self.draw_graph()

    def draw_graph(self):
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

