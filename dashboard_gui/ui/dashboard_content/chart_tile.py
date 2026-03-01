import os
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy_garden.graph import Graph, LinePlot
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Rectangle, Color
from kivy.uix.floatlayout import FloatLayout

from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.global_state_manager import GLOBAL_STATE
import config

class ChartTile(ButtonBehavior, BoxLayout):

    def __init__(self, title, unit, color_rgba, bg=None, **kw):
        ButtonBehavior.__init__(self)
        BoxLayout.__init__(
            self,
            orientation="vertical",
            spacing=dp_scaled(6),
            padding=dp_scaled(6),
            **kw
        )
        self._last_unit = unit
        self.title = title
        self.unit = unit
        self.color = color_rgba
        self.window = config.get_tile_graph_window()
        self.buffer = []
        self._coord_buffers = {}  # NEU: für interne/externe Koordinaten
        self.last_value = None
        self.smoothing = 0.25

        self._trend_results = {}       # Die fertigen Pfeile
        # Multi-Device Buffers: device_id → eigener Verlauf
        self.buffers = {}

        # -------------------------------------------------
        # BACKGROUND
        # -------------------------------------------------
        if bg:
            self.bg_path = os.path.join("dashboard_gui", "assets", "tiles", bg)
        else:
            self.bg_path = None

        with self.canvas.before:
            if self.bg_path:
                self.bg_rect = Rectangle(source=self.bg_path, pos=self.pos, size=self.size)
            else:
                Color(0, 0, 0, 0)
                self.bg_rect = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=self._upd_bg, size=self._upd_bg)
        self.base_unit = unit   # z. B. "°C" oder "kPa"

        # -------------------------------------------------
        # HEADER (TITLE • TREND • VALUE)
        # -------------------------------------------------
        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp_scaled(38),
            spacing=dp_scaled(4),
        )
        
        # Titel (nimmt den restlichen Platz ein)
        self.lbl_title = Label(
            text=title, 
            font_size=sp_scaled(16),
            halign="left",
            valign="middle"
        )
        self.lbl_title.bind(size=self.lbl_title.setter('text_size')) # Linksbündig fixieren

        # Trend Icon
        self.lbl_trend = Label(
            text="", 
            font_size=sp_scaled(20), 
            font_name="FA",
            size_hint_x=None,
            width=dp_scaled(30)
        )
        
        # MAIN VALUE — Sauber und ohne Schatten
        self.lbl_value = Label(
            text="--",
            font_size=sp_scaled(28), # Leicht reduziert für bessere Proportionen
            color=self.color,
            bold=True,
            size_hint_x=None,
            width=dp_scaled(120) # Fixe Breite für stabiles Layout
        )
        
        header.add_widget(self.lbl_title)
        header.add_widget(self.lbl_trend)
        header.add_widget(self.lbl_value)
        self.add_widget(header)
        # -------------------------------------------------
        # GRAPH
        # -------------------------------------------------
        self.graph = Graph(
            xlabel="", ylabel="",
            x_ticks_major=0, x_ticks_minor=0,
            y_ticks_major=0, y_ticks_minor=0,
            x_grid_label=False, y_grid_label=False,
            draw_border=False,
            padding=dp_scaled(4),
            xmin=0, xmax=self.window,
            ymin=0, ymax=1,
            background_color=(0, 0, 0, 0),
            tick_color=(0, 0, 0, 0),
            size_hint=(1, 1),
        )

        self.plot = LinePlot(color=self.color, line_width=4.0)
        self.graph.add_plot(self.plot)
        glow = [self.color[0], self.color[1], self.color[2], 0.25]
        self.plot_glow = LinePlot(color=glow, line_width=4.0)
        self.graph.add_plot(self.plot_glow)

        self.add_widget(self.graph)

        # -------------------------------------------------
        # FOOTER
        # -------------------------------------------------
        footer = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp_scaled(22),
            spacing=dp_scaled(4),
        )

        self.lbl_avg = Label(text="avg: --", font_size=sp_scaled(16))
        self.lbl_minmax = Label(text="", font_size=sp_scaled(16))

        footer.add_widget(self.lbl_avg)
        footer.add_widget(self.lbl_minmax)

        self.add_widget(footer)


    # -------------------------------------------------
    # BACKGROUND UPDATE
    # -------------------------------------------------
    def _upd_bg(self, *_):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    # -------------------------------------------------
    # UPDATE
    # -------------------------------------------------
    def update(self, value, buf_key, render=False):
        # 1. Daten an den GSM senden (Zentrale Speicherung)
        GLOBAL_STATE.process_new_value(buf_key, value)

        if render:
            # 2. Daten für die Anzeige wieder vom GSM holen
            history = GLOBAL_STATE.get_graph_data(buf_key)
            
            # Icon vom GSM holen
            self.lbl_trend.text = GLOBAL_STATE.get_trend_icon(buf_key)
            
            # Wert anzeigen
            if history:
                current_val = history[-1]
                self.lbl_value.text = f"{current_val:.2f} {self.unit}"
                self._render_buffer(history)

    def _render_buffer(self, buf):
        # 1. Punkte für den Plot erstellen
        pts = [(i, val) for i, val in enumerate(buf)]
        self.plot.points = pts
        self.plot_glow.points = pts
    
        # 2. Y-Achse (Höhe) automatisch anpassen
        if len(buf) > 0:
            mn = min(buf)
            mx = max(buf)
            if mn == mx:
                mn -= 0.5
                mx += 0.5
            margin = (mx - mn) * 0.2
            self.graph.ymin = mn - margin
            self.graph.ymax = mx + margin
    
        # 3. X-Achse (Breite) - DAS IST DIE ÄNDERUNG:
        # Wenn wir weniger Daten haben als ins Fenster passen, 
        # setzen wir xmax auf die aktuelle Anzahl (mindestens 1).
        # Sobald wir mehr haben, bleibt xmax beim eingestellten "window".
        if len(buf) < self.window:
            # Graph füllt sich von links nach rechts
            self.graph.xmax = max(1, len(buf) - 1)
        else:
            # Fenster ist voll, Graph fängt an zu laufen/stauchen
            self.graph.xmax = self.window - 1
    
        # 4. Footer-Texte (Durchschnitt/Min/Max)
        if len(buf) > 1:
            avg_v = sum(buf) / len(buf)
            self.lbl_avg.text = f"avg: {avg_v:.2f}"
            self.lbl_minmax.text = f"min: {mn:.2f}  max: {mx:.2f}"
        else:
            self.lbl_avg.text = "avg: --"
            self.lbl_minmax.text = ""
    # -------------------------------------------------
    # RESET
    # -------------------------------------------------
    def reset(self):
        self.lbl_value.text = "--"
        self.lbl_trend.text = ""
        self.lbl_avg.text = "avg: --"
        self.lbl_minmax.text = ""

        self.buffers = {}
        self.last_value = None
        self.plot.points = []
        self.plot_glow.points = []
        self.graph.ymin = 0
        self.graph.ymax = 1

    # -------------------------------------------------
    # TILE CLICK → FULLSCREEN
    # -------------------------------------------------
    def on_release(self, *_):
        parent = self.parent
        sm = None
        while parent:
            if hasattr(parent, "current") and hasattr(parent, "get_screen"):
                sm = parent
                break
            parent = parent.parent

        if sm is None:
            print("❌ ERROR: Kein ScreenManager gefunden!")
            return

        if not sm.has_screen("fullscreen"):
            print("❌ ERROR: Fullscreen existiert nicht!")
            return

        dashboard = sm.get_screen("dashboard")
        for key, tile in dashboard.content.tile_map.items():
            if tile is self:
                fs = sm.get_screen("fullscreen")
                fs.activate_tile(key)
                sm.current = "fullscreen"
                return

        print("❌ ERROR: Tile-Key nicht gefunden!")

    def get_mixed_buffer(self):
        from dashboard_gui.global_state_manager import GLOBAL_STATE
    
        merged = []
    
        for key in GLOBAL_STATE.mixed_selected_buffers:
            buf = self.buffers.get(key)
            if buf:
                merged.extend(buf)
    
        merged.sort(key=lambda x: x if isinstance(x, float) else x["value"])
        return merged[-self.window:]
    def apply_graph_window(self, new_window: int):
        if new_window <= 0:
            return
    
        self.window = int(new_window)
    
        # alle Float-Buffer trimmen
        for key, buf in self.buffers.items():
            if len(buf) > self.window:
                self.buffers[key] = buf[-self.window:]
    
        # Coord-Buffer trimmen
        if hasattr(self, "_coord_buffers"):
            for key, buf in self._coord_buffers.items():
                if len(buf) > self.window:
                    self._coord_buffers[key] = buf[-self.window:]
    
        # Graph neu rendern (falls Daten da)
        for buf in self.buffers.values():
            if buf:
                self._render_buffer(buf)
                break        
