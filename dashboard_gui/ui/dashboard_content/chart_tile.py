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
from dashboard_gui.ui.formatters import UIFormatter

import config

class ChartTile(ButtonBehavior, BoxLayout):
    def __init__(self, tile_id, title, unit, color_rgba, bg=None, **kw):
        ButtonBehavior.__init__(self, **kw)
        # Wichtig: orientation="vertical" sorgt dafür, dass Header und Graph-Container untereinander liegen
        BoxLayout.__init__(self, orientation="vertical", spacing=dp_scaled(2), padding=dp_scaled(6))
        
        self.tile_id = tile_id
        self.title = title
        self.unit = unit
        self._last_val = None
        self._last_avg = None
        self._last_min = None
        self._last_max = None
        self.color = color_rgba
        self.window = config.get_tile_graph_window()
        self._frame_skip = 0
        # -------------------------------------------------
        # 1. HINTERGRUND
        # -------------------------------------------------
        self.bg_path = os.path.join("dashboard_gui", "assets", "tiles", bg) if bg else None
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            if self.bg_path and os.path.exists(self.bg_path):
                self.bg_rect.source = self.bg_path
        self.bind(pos=self._upd_bg, size=self._upd_bg)

        # -------------------------------------------------
        # 2. HEADER (Feste Höhe)
        # -------------------------------------------------
        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp_scaled(50), padding=[dp_scaled(4), 0])
        self.lbl_main_info = Label(
            text=title, 
            markup=True, 
            halign="left", 
            valign="top", # Text oben ausrichten für modernen Look
            outline_width=1,
            outline_color=(0,0,0,0.2)
        )
        self.lbl_main_info.bind(size=self.lbl_main_info.setter('text_size'))
        header.add_widget(self.lbl_main_info)
        self.add_widget(header)

# -------------------------------------------------
        # 3. GRAPH CONTAINER
        # -------------------------------------------------
        self.graph_container = FloatLayout(size_hint=(1, 1))
        
        # 1. Zuerst den Graphen (liegt ganz unten)
        self.graph = Graph(
            draw_border=False, 
            background_color=(0,0,0,0),
            padding=dp_scaled(15), # Mehr Platz zu den Rändern
            xmin=0, xmax=self.window, ymin=0, ymax=1,
            size_hint=(1, 1), 
            pos_hint={'x': 0, 'y': 0}
        )
        
        self.plot = LinePlot(color=self.color, line_width=dp_scaled(2.2))
        self.plot_glow = LinePlot(color=[*self.color[:3], 0.15], line_width=dp_scaled(4))
        ## self.graph.add_plot(self.plot_glow) # Glow-Effekt (optional, kann die Performance beeinträchtigen)
        self.graph.add_plot(self.plot)
        self.graph_container.add_widget(self.graph)

        # 2. JETZT DIE LABELS (Werden NACH dem Graphen hinzugefügt -> liegen darüber)
        
        # AVG (unten rechts)
        self.lbl_avg = Label(
            text="avg: --", 
            font_size=sp_scaled(16), # Kleiner ist oft edler
            color=(1, 1, 1, 0.5),    # Halbe Transparenz für Hintergrund-Feeling
            size_hint=(None, None),
            size=(dp_scaled(120), dp_scaled(20)),
            pos_hint={'right': 0.98, 'top': 0.95}, # Nach oben verschoben
            halign="right"
        )
        self.lbl_avg.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)))

        # MIN/MAX Box (unten links)
        # MIN/MAX Box (Unten als horizontale Leiste statt vertikal gequetscht)
        self.minmax_box = BoxLayout(
            orientation="horizontal", # Horizontal wirkt breiter/stabiler
            size_hint=(1, None),
            height=dp_scaled(20),
            pos_hint={'x': 0, 'y': 0.02},
            padding=[dp_scaled(10), 0],
            spacing=dp_scaled(15)
        )
        
        self.lbl_min = Label(text="min: --", font_size=sp_scaled(16), color=(1,1,1,0.4), halign="left")
        self.lbl_max = Label(text="max: --", font_size=sp_scaled(16), color=(1,1,1,0.4), halign="left")
        
        for l in [self.lbl_min, self.lbl_max]:
            l.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)))
        
        self.minmax_box.add_widget(self.lbl_max)
        self.minmax_box.add_widget(self.lbl_min)
        
        # Diese add_widget Aufrufe kommen nach dem Graphen!
        self.graph_container.add_widget(self.lbl_avg)
        self.graph_container.add_widget(self.minmax_box)
        
        self.add_widget(self.graph_container)

    def _upd_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size


    # UPDATE – Die Steuerzentrale
    # -------------------------------------------------
    def update(self, value, buf_key, render=False):
        if value is not None:
            GLOBAL_STATE.graph_engine.process_new_value(buf_key, value)
    
        if not render:
            return
    
        history = GLOBAL_STATE.get_graph_data(buf_key)
        unit = GLOBAL_STATE.get_unit(buf_key)
    
        if not history:
            self.lbl_main_info.text = f"[color=#666666]{self.title}: --[/color]"
            self._render_empty_graph()
            return
    
        last_val = history[-1]
        trend_icon = GLOBAL_STATE.get_trend_icon(buf_key)
    
        if last_val != self._last_val:
            self.lbl_main_info.text = UIFormatter.format_sensor_label(
                name=self.title,
                value=last_val,
                unit=unit,
                trend=trend_icon,
                sz_val=28,
                sz_name=14,
                sz_trend=20,
                sz_unit=14
            )
            self._last_val = last_val
    
        self._render_buffer(history, unit, buf_key)
    # -------------------------------------------------
    # RENDER EMPTY – Alles auf Null/Striche setzen
    # -------------------------------------------------
# -------------------------------------------------
    # RENDER EMPTY – Alles auf Null/Striche setzen
    # -------------------------------------------------
    def _render_empty_graph(self):
        """Löscht die Linien im Graph und setzt Stats auf Platzhalter."""
        self.plot.points = []
        self.plot_glow.points = []
        
        # FIX: Hier waren die alten Namen drin!
        self.lbl_avg.text = "avg: ---"
        self.lbl_min.text = "min: ---"
        self.lbl_max.text = "max: ---"
        
        # Y-Achse resetten
        self.graph.ymin = 0
        self.graph.ymax = 1

    # -------------------------------------------------
    # RENDER BUFFER – Den echten Graph zeichnen
    # -------------------------------------------------
    def _render_buffer(self, buf, unit, buf_key):
        # Sicherheitscheck: Wir brauchen min. 2 Punkte für eine Linie
        if not buf or len(buf) < 2: 
            self._render_empty_graph()
            return
    
        # 1. Fenster berechnen (X-Achse)
        current_count = len(buf)
        display_buf = list(buf)[-self.window:] # Nur das sichtbare Fenster
        
        self.graph.xmin = 0
        self.graph.xmax = (len(display_buf) - 1)
    
        # 2. Skalierung berechnen (Y-Achse) mit 5% Puffer
        mn_val = min(display_buf)
        mx_val = max(display_buf)
        
        if mn_val == mx_val:
            # Falls alle Werte gleich sind (flache Linie), künstlichen Raum schaffen
            self.graph.ymin = mn_val - 1.0
            self.graph.ymax = mx_val + 1.0
        else:
            diff = mx_val - mn_val
            self.graph.ymin = mn_val - (diff * 0.05)
            self.graph.ymax = mx_val + (diff * 0.05)
    
        # 3. Punkte setzen
        pts = [(i, val) for i, val in enumerate(display_buf)]
        self.plot.points = pts
        self.plot_glow.points = pts
    
# 4. Statistiken aus der Engine holen
        avg_v, mn_stat, mx_stat = GLOBAL_STATE.graph_engine.get_stats(buf_key)
        
        if avg_v is not None:
            self.lbl_avg.text = f"avg: {avg_v:.2f} {unit}"
            self.lbl_min.text = f"min: {mn_stat:.2f}{unit}"
            self.lbl_max.text = f"max: {mx_stat:.2f}{unit}"
        else:
            self.lbl_avg.text = "avg: ---"
            self.lbl_min.text = "min: ---"
            self.lbl_max.text = "max: ---"
    # -------------------------------------------------
    # RESET
    # -------------------------------------------------
# -------------------------------------------------
    # RESET - Zurück auf Werkseinstellungen
    # -------------------------------------------------
    def reset(self):
        """Bereinigt das Tile komplett."""
        # Titel auf grau/leer setzen
        self.lbl_main_info.text = f"[color=#666666]{self.title}[/color]"
        
        # Die Graph-Stats säubern (ruft den Fix von oben auf)
        self._render_empty_graph()
        
        # Falls du den last_value speicherst:
        if hasattr(self, 'last_value'):
            self.last_value = None
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
