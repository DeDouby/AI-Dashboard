import os
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy_garden.graph import Graph, LinePlot
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Rectangle, Color
from kivy.uix.floatlayout import FloatLayout
from kivy.app import App  # <--- Das hier fehlt!
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.global_state_manager import GLOBAL_STATE
from kivy.uix.anchorlayout import AnchorLayout
import config

class ChartTile(ButtonBehavior, BoxLayout):
    def __init__(self, tile_id, title, unit, color_rgba, bg=None, **kw):
        # Wir rufen die Super-Klassen auf
        ButtonBehavior.__init__(self, **kw)
        BoxLayout.__init__(self, orientation="vertical", spacing=dp_scaled(6), padding=dp_scaled(6))
        
        self.tile_id = tile_id
        self.title = title
        self.unit = unit
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
        footer = AnchorLayout(
            anchor_x='center',  # horizontal zentrieren
            anchor_y='center',  # vertical zentrieren
            size_hint_y=None,
            height=dp_scaled(22)
        )
        lbl_box = BoxLayout(orientation='horizontal', spacing=dp_scaled(4))
        self.lbl_avg = Label(text="avg: --", font_size=sp_scaled(16))
        self.lbl_minmax = Label(text="", font_size=sp_scaled(16))
        lbl_box.add_widget(self.lbl_avg)
        lbl_box.add_widget(self.lbl_minmax)
        
        footer.add_widget(lbl_box)
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
        # 1. Wert in den Graph-Speicher schieben
        GLOBAL_STATE.graph_engine.process_new_value(buf_key, value)
    
        if render:
            history = GLOBAL_STATE.get_graph_data(buf_key)
    
            # ✅ Trend holen
            trend_icon = GLOBAL_STATE.get_trend_icon(buf_key)
            self.lbl_trend.text = trend_icon or ""
            self.lbl_trend.font_name = "FA"
    
            # ✅ Einheit vom GSM holen
            unit = GLOBAL_STATE.get_unit(buf_key)
            self._render_buffer(history, unit, buf_key)
            if history:
                # Letzten Wert anzeigen
                last_val = history[-1]
                self.lbl_value.text = f"{last_val:.2f} {unit}"
                
                # Graph zeichnen (Hier rufen wir die Helferfunktion auf)
                self._render_buffer(history, unit, buf_key)

    def _render_buffer(self, buf, unit, buf_key):
        if not buf: 
            return
    
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
    
        # Stats aus GraphEngine
        avg_v, mn_stat, mx_stat = GLOBAL_STATE.graph_engine.get_stats(buf_key)
    
        if avg_v is not None:
            # Einheit für avg + min/max anwenden
            self.lbl_avg.text = f"avg: {avg_v:.2f} {unit}"
            self.lbl_minmax.text = f"min: {mn_stat:.2f} {unit}  max: {mx_stat:.2f} {unit}"
        else:
            self.lbl_avg.text = "avg: --"
            self.lbl_minmax.text = ""
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
# -------------------------------------------------
    # TILE CLICK → FULLSCREEN (GGM Version)
    # -------------------------------------------------
    def on_release(self):
        idx = GLOBAL_STATE.get_active_index()
        dev_list = GLOBAL_STATE.get_device_list()
        if not dev_list or idx >= len(dev_list): return
            
        # SICHERES EXTRAHIEREN (Idiotensicher)
        item = dev_list[idx]
        dev_id = item.get("device_id") if isinstance(item, dict) else item
        
        channel = GLOBAL_STATE.get_active_channel()
        full_key = f"{dev_id}_{channel}_{self.tile_id}"
        
        if hasattr(GLOBAL_STATE, "ggm"):
            GLOBAL_STATE.ggm.engines["dashboard"].open_fullscreen(full_key)
