# csv_viewer_graphs.py – Dark-Pro Edition
# ------------------------------------------

import csv
import math

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy_garden.graph import Graph, LinePlot
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.behaviors import ButtonBehavior

from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled


class CSVGraphView(BoxLayout):
    """
    Modernisierte Dark-Pro Version des CSV-Graphen:
    - Multi Series (T_i, H_i, T_e, H_e, rssi)
    - Smoothing identisch zu deinen ChartTiles
    - Glow-Linien
    - Autoscaling
    - Zoom + Drag
    - Reset-Button
    """

    def __init__(self, **kw):
        super().__init__(**kw)
    
        # Layout
        self.orientation = "vertical"
        self.spacing = dp_scaled(6)
        self.padding = dp_scaled(6)
        self._drag_deadzone = dp_scaled(3)  # 3dp Noise-Filter

        # ---------------------------------------------------------
        # VIEW STATE (CLEAN, EINDEUTIG)
        # ---------------------------------------------------------
        self._zoom_x = 1.0        # Zoom Zeitachse
        self._zoom_y = 1.0        # Zoom Y
        self._pan_y = 0.0         # Y-Pan
        self._x_center = None     # Zeit-Mittelpunkt (Index)
        self._drag_start = None  # aktiver Drag
    
        # ---------------------------------------------------------
        # DATA
        # ---------------------------------------------------------
        self.csv_path = None
        self.data_series = {}     # {col: [raw]}
        self.smoothed = {}        # {col: [smoothed]}
        self.window = 300
        self.smoothing = 0.25

        # ---------------------------------------------------------
        # COLORS – kompatibel zu deinen ChartTiles
        # ---------------------------------------------------------
        self.colors = {
            "T_i":  (0.30, 0.90, 1.00, 1),   # Cyan – innen Temp
            "H_i":  (0.30, 1.00, 0.30, 1),   # Grün – innen Hum
            "T_e":  (1.00, 0.80, 0.30, 1),   # Amber – außen Temp
            "H_e":  (0.80, 0.60, 1.00, 1),   # Violett – außen Hum
            "rssi": (1.00, 0.40, 0.40, 1),   # Rot – RSSI
        }

        # ---------------------------------------------------------
        # HEADER (Dark-Pro)
        # ---------------------------------------------------------
        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp_scaled(36),
            spacing=dp_scaled(6),
            padding=[dp_scaled(6), 0],
        )

        self.lbl_title = Label(
            text="Graph Ansicht",
            font_size=sp_scaled(18),
            halign="left",
            valign="middle",
            color=(0.95, 0.95, 0.98, 1),
        )
        self.lbl_title.bind(size=lambda *_: self.lbl_title.texture_update())
        header.add_widget(self.lbl_title)

        # Reset Zoom Button
        btn_reset = Button(
            text="Reset Zoom",
            size_hint=(None, 1),
            width=dp_scaled(120),
            background_down="",
            background_color=(0.15, 0.22, 0.55, 1),
            color=(0.95, 0.95, 0.98, 1),
            font_size=sp_scaled(14),
        )
        btn_reset.bind(on_release=self._reset_view)

        header.add_widget(btn_reset)

        self.add_widget(header)

        # ---------------------------------------------------------
        # GARDEN GRAPH – Dark-Pro Setup
        # ---------------------------------------------------------
        self.graph = Graph(
            xlabel="",
            ylabel="",
            x_ticks_major=0,
            x_ticks_minor=0,
            y_ticks_major=0,
            y_ticks_minor=0,
            x_grid_label=False,
            y_grid_label=False,
            draw_border=False,
            padding=dp_scaled(4),
            xmin=0,
            xmax=self.window,
            ymin=0,
            ymax=1,
            background_color=(0.05, 0.05, 0.07, 1),
            tick_color=(0.2, 0.2, 0.25, 1),
            size_hint=(1, 1),
        )

        # ZOOM + DRAG HANDLING
        self.graph.bind(on_touch_down=self._on_touch_down)
        self.graph.bind(on_touch_move=self._on_touch_move)
        self.graph.bind(on_touch_up=self._on_touch_up)


        # PLots
        self.plots_main = {}
        self.plots_glow = {}

        for col, c in self.colors.items():
            # Hauptlinie
            p_main = LinePlot(color=c, line_width=2.2)
            self.graph.add_plot(p_main)
            self.plots_main[col] = p_main

            # Glow-Linie
            glow = [c[0], c[1], c[2], 0.25]
            p_glow = LinePlot(color=glow, line_width=5.5)
            self.graph.add_plot(p_glow)
            self.plots_glow[col] = p_glow

        self.add_widget(self.graph)

        # ---------------------------------------------------------
        # FOOTER – Stats
        # ---------------------------------------------------------
        footer = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp_scaled(24),
            spacing=dp_scaled(6),
            padding=[dp_scaled(4), 0],
        )

        self.lbl_stats = Label(
            text="",
            font_size=sp_scaled(12),
            color=(0.85, 0.85, 0.92, 1),
            halign="left",
            valign="middle",
        )
        self.lbl_stats.bind(size=lambda *_: self.lbl_stats.texture_update())
        footer.add_widget(self.lbl_stats)

        self.add_widget(footer)

        # Live redrawing
        self.bind(size=lambda *_: self._redraw())

    # ---------------------------------------------------------
    # PUBLIC API
    # ---------------------------------------------------------
    def set_csv_path(self, p):
        self.csv_path = p
        self._read_csv()
        # Startansicht: rechts (neueste Daten)
        max_len = max((len(v) for v in self.smoothed.values()), default=0)
        self._x_center = max_len
        self._redraw()

    # ---------------------------------------------------------
    # CSV LESEN + SMOOTHING
    # ---------------------------------------------------------
    def _read_csv(self):
        self.data_series = {k: [] for k in self.colors.keys()}

        if not self.csv_path:
            return

        try:
            with open(self.csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    for col in self.colors.keys():
                        raw_val = row.get(col)
                        if not raw_val:
                            continue
                        try:
                            v = float(raw_val)
                            self.data_series[col].append(v)
                        except:
                            pass
        except Exception as e:
            print("[CSVGraphView] Error:", e)
            return

        # Auf Fenstergröße kürzen
        for col in self.data_series:
            arr = self.data_series[col]
            if len(arr) > self.window:
                self.data_series[col] = arr[-self.window:]

        # Smoothe Serien erzeugen
        self.smoothed = {k: [] for k in self.colors}
        for col, arr in self.data_series.items():
            last = None
            out = []
            for v in arr:
                if last is None:
                    sm = v
                else:
                    sm = last * (1 - self.smoothing) + v * self.smoothing
                out.append(sm)
                last = sm
            self.smoothed[col] = out

    # ---------------------------------------------------------
    # GRAPH RESET
    # ---------------------------------------------------------
    def _reset_view(self, *_):
        print("[CSVGraphView] RESET pressed")
    
        self._zoom_x = 1.0
        self._zoom_y = 1.0
        self._pan_y = 0.0
        self._drag_start = None
    
        max_len = max((len(v) for v in self.smoothed.values()), default=0)
        self._x_center = max_len
    
        self._redraw()
    # ---------------------------------------------------------
    # RENDER / REDRAW
    # ---------------------------------------------------------
    def _redraw(self):

        all_vals = []
        for arr in self.smoothed.values():
            all_vals.extend(arr)

        if not all_vals:
            for col in self.colors:
                self.plots_main[col].points = []
                self.plots_glow[col].points = []
            self.graph.ymin = 0
            self.graph.ymax = 1
            return

        mn = min(all_vals)
        mx = max(all_vals)
        
        if math.isclose(mn, mx):
            mn -= 0.5
            mx += 0.5
        
        # Base-Spans + Margin (damit Reset "normal" aussieht)
        base_span_y = (mx - mn)
        base_margin = base_span_y * 0.15
        base_ymin = mn - base_margin
        base_ymax = mx + base_margin
        base_mid_y = (base_ymin + base_ymax) * 0.5
        base_span_y = (base_ymax - base_ymin)
        
        # Zoom clamp (verhindert kaputte Zustände)
        self._zoom_y = max(0.1, min(50.0, self._zoom_y))
        self._zoom_x = max(0.1, min(50.0, self._zoom_x))
        
        # Y mit Zoom+Pan
        span_y = base_span_y / self._zoom_y
        self.graph.ymin = base_mid_y - span_y / 2 + self._pan_y
        self.graph.ymax = base_mid_y + span_y / 2 + self._pan_y
        
        # X (Zeit) – NUR über _x_center
        max_len = max(len(arr) for arr in self.smoothed.values())
        if max_len <= 1:
            self.graph.xmin = 0
            self.graph.xmax = 1
        else:
            # falls noch nicht gesetzt (z.B. wenn _redraw vor set_csv_path läuft)
            if self._x_center is None:
                self._x_center = max_len

            span_x = max_len / self._zoom_x
            span_x = max(5.0, span_x)  # Minimum Fenster, damit es nicht kollabiert

            # clamp center, damit du nicht "aus dem Chart" scrollst
            half = span_x / 2
            self._x_center = max(half, min(max_len - half, self._x_center))

            self.graph.xmin = self._x_center - half
            self.graph.xmax = self._x_center + half


        # Punkte setzen
        for col, arr in self.smoothed.items():
            pts = [(i, v) for i, v in enumerate(arr)]
            self.plots_main[col].points = pts
            self.plots_glow[col].points = pts

        # Footer
        used_cols = [col for col, arr in self.smoothed.items() if arr]
        self.lbl_stats.text = f"{max_len} Punkte • {', '.join(used_cols)}"

    # ---------------------------------------------------------
    # DRAG / ZOOM Handling
    # ---------------------------------------------------------
    def _on_touch_down(self, inst, touch):
        if not self.graph.collide_point(*touch.pos):
            return False
    
        if hasattr(touch, "button"):
            if touch.button == "scrolldown":
                self._zoom_x *= 1.15
                self._zoom_y *= 1.15
                self._redraw()
                return True
            elif touch.button == "scrollup":
                self._zoom_x *= 0.87
                self._zoom_y *= 0.87
                self._redraw()
                return True
    
        touch.grab(self.graph)
        self._drag_start = touch.pos[:]
        return True

    def _on_touch_move(self, inst, touch):
        if touch.grab_current is not self.graph:
            return False
        if not self._drag_start:
            return False
    
        dx_px = touch.pos[0] - self._drag_start[0]
        dy_px = touch.pos[1] - self._drag_start[1]
    
        if abs(dx_px) < self._drag_deadzone and abs(dy_px) < self._drag_deadzone:
            return True
    
        xspan = max(1e-9, (self.graph.xmax - self.graph.xmin))
        yspan = max(1e-9, (self.graph.ymax - self.graph.ymin))
    
        gw = max(1.0, float(self.graph.width))
        gh = max(1.0, float(self.graph.height))
    
        self._x_center -= (dx_px / gw) * xspan
        self._pan_y -= (dy_px / gh) * yspan
    
        self._drag_start = touch.pos[:]
        self._redraw()
        return True

    def _on_touch_up(self, inst, touch):
        if touch.grab_current is self.graph:
            touch.ungrab(self.graph)
        self._drag_start = None
        return True


