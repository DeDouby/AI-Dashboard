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
        # Wir speichern die initiale Unit nur noch als Fallback, 
        # die echte Unit kommt jetzt aus der unit_map des GSM.
        self.title = title
        self.color = color_rgba
        self.window = config.get_tile_graph_window()

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
            # Padding erhöhen: links, unten, rechts, oben
            # dp_scaled(8) gibt der Linie genug Platz zum "Atmen"
            padding=dp_scaled(8), 
            xmin=0, xmax=self.window,
            ymin=0, ymax=1,
            background_color=(0, 0, 0, 0),
            tick_color=(0, 0, 0, 0),
            size_hint=(1, 1),
        )

        # Dickere Linien für den "Vivid" Look
        self.plot = LinePlot(color=self.color, line_width=dp_scaled(3.5)) 
        self.plot_glow = LinePlot(color=[*self.color[:3], 0.2], line_width=dp_scaled(7))
        self.graph.add_plot(self.plot_glow)
        self.graph.add_plot(self.plot)
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
    # UPDATE – Jetzt mit dynamischer Unit-Abfrage
    # -------------------------------------------------
    def update(self, value, buf_key, render=False):
        # 1. Wert an GSM geben (Smoothing passiert dort!)
        GLOBAL_STATE.process_new_value(buf_key, value)

        if render:
            # 2. Daten & Trend vom GSM holen
            history = GLOBAL_STATE.get_graph_data(buf_key)
            self.lbl_trend.text = GLOBAL_STATE.get_trend_icon(buf_key)
            
            # 3. EINHEIT DYNAMISCH HOLEN (Der Fullscreen-Weg)
            # Das ist der Fix: Wir nutzen die unit_map aus dem GSM
            current_unit = GLOBAL_STATE.get_unit(buf_key)

            if history:
                # Letzten Wert mit der ECHTEN Einheit anzeigen
                last_val = history[-1]
                self.lbl_value.text = f"{last_val:.2f} {current_unit}"
                
                # Graph zeichnen
                self._render_buffer(history, current_unit)

    def _render_buffer(self, buf, unit):
        if not buf: 
            return
        # ... (deine X-Achsen Logik bleibt gleich) ...
        current_count = len(buf)
        self.graph.xmin = 0
        self.graph.xmax = (current_count - 1) if current_count < self.window else (self.window - 1)

        display_buf = buf[-self.window:]
        pts = [(i, val) for i, val in enumerate(display_buf)]
        self.plot.points = pts
        self.plot_glow.points = pts
    
        # Y-Achse mit 5% Margin
        mn, mx = min(display_buf), max(display_buf)
        if mn == mx:
            mn -= 0.5; mx += 0.5
        
        diff = mx - mn
        self.graph.ymin = mn - diff * 0.05
        self.graph.ymax = mx + diff * 0.05
        
        # 4. FOOTER UPDATEN – Auch hier die dynamische Einheit nutzen!
        avg_v = sum(display_buf) / len(display_buf)
        self.lbl_avg.text = f"avg: {avg_v:.2f} {unit}"
        self.lbl_minmax.text = f"min: {mn:.2f}  max: {mx:.2f}"
####
    # -------------------------------------------------
    # RESET
    # -------------------------------------------------
    def reset(self):
        self.lbl_value.text = "--"
        self.lbl_trend.text = ""
        self.lbl_avg.text = "avg: --"
        self.lbl_minmax.text = ""

        self.last_value = None
        self.plot.points = []
        self.plot_glow.points = []
        self.graph.ymin = 0
        self.graph.ymax = 1
####
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


    
        merged.sort(key=lambda x: x if isinstance(x, float) else x["value"])
        return merged[-self.window:]
 
 
