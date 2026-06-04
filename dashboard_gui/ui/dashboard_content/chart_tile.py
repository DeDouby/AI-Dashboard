from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy_garden.graph import Graph, LinePlot
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Rectangle, Color, RoundedRectangle, Mesh
from kivy.uix.floatlayout import FloatLayout
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.formatters import UIFormatter
import config

class ChartTile(ButtonBehavior, BoxLayout):
    def __init__(self, tile_id, title, unit, color_rgba, **kw):
        ButtonBehavior.__init__(self, **kw)
        BoxLayout.__init__(self, orientation="vertical", spacing=dp_scaled(2), padding=dp_scaled(8))
        
        self.tile_id = tile_id
        self.title = title
        self.unit = unit
        self._last_val = None
        self._last_avg = None
        self._last_min = None
        self._last_max = None
        self.color = color_rgba
        self.window = config.get_tile_graph_window()

        # -------------------------------------------------
        # 1. MODERNISIERTER BACKGROUND (Jetzt noch transparenter!)
        # -------------------------------------------------
        with self.canvas.before:
            Color(0.08, 0.08, 0.10, 0.40)
        
            self.bg_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp_scaled(2)]
            )
        
        self.bind(pos=self._upd_bg, size=self._upd_bg)

        # -------------------------------------------------
        # 2. HEADER & LIVE-WERT (Fokus auf große Typografie)
        # -------------------------------------------------
        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp_scaled(30), padding=[dp_scaled(6), 0])
        self.lbl_main_info = Label(
            text=title, 
            markup=True, 
            halign="left", 
            valign="middle",
            font_size=sp_scaled(36),
            bold=True,
            color=(1,1,1,0.9),
            outline_width=1,
            outline_color=(0,0,0,0.15)
        )
        self.lbl_main_info.bind(size=self.lbl_main_info.setter('text_size'))
        header.add_widget(self.lbl_main_info)
        self.add_widget(header)

        # -------------------------------------------------
        # 3. GRAPH CONTAINER & GRAFIK-ENGINE
        # -------------------------------------------------
        self.graph_container = FloatLayout(size_hint=(1, 1))
        
        self.graph = Graph(
            draw_border=False, 
            background_color=(0,0,0,0),
            padding=dp_scaled(0), 
            xmin=0, xmax=self.window, ymin=0, ymax=1,
            size_hint=(1, 1), 
            pos_hint={'x': 0, 'y': 0}
        )
        
        # Plot-Linie dicker für professionellen Look (Anti-Aliased Style)
        self.plot = LinePlot(color=self.color, line_width=dp_scaled(2.5))
        self.graph.add_plot(self.plot)
        self.graph_container.add_widget(self.graph)

        # -------------------------------------------------
        # 4. TRANSTRANSQUARENTE FILL-FLÄCHE (Unterschwelliges Leuchten)
        # -------------------------------------------------
        with self.graph.canvas.after:
            self.mesh_color = Color(self.color[0], self.color[1], self.color[2], 0.25)
            # WICHTIG: triangle_strip statt triangle_fan
            self.mesh = Mesh(mode='triangle_strip')
            
        self.graph.bind(pos=self._upd_mesh, size=self._upd_mesh)

        # -------------------------------------------------
        # 5. STATS LABELS (Subtil im Hintergrund gedimmt)
        # -------------------------------------------------
        self.lbl_avg = Label(
            text="avg: --", 
            font_size=sp_scaled(20), 
            bold=True,
            color=(1, 1, 1, 0.7),    # Gedimmtes Weiß
            size_hint=(None, None),
            size=(dp_scaled(140), dp_scaled(20)),
            pos_hint={'right': 0.96, 'top': 0.95}, 
            halign="right"
        )
        self.lbl_avg.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)))

        self.minmax_box = BoxLayout(
            orientation="horizontal", 
            size_hint=(1, None),
            height=dp_scaled(20),
            pos_hint={'x': 0.1, 'y': 0.13},
            padding=[dp_scaled(12), 0],
            spacing=dp_scaled(20)
        )
        
        self.lbl_min = Label(text="min: --", font_size=sp_scaled(18), bold=True, color=(1,1,1,0.7), halign="left")
        self.lbl_max = Label(text="max: --", font_size=sp_scaled(18), bold=True, color=(1,1,1,0.7), halign="left")
        
        for l in [self.lbl_min, self.lbl_max]:
            l.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)))
        
        self.minmax_box.add_widget(self.lbl_max)
        self.minmax_box.add_widget(self.lbl_min)
        self.graph_container.add_widget(self.lbl_avg)   
        self.graph_container.add_widget(self.minmax_box)

        # DEZENTE ZEITACHSE UNTER MIN/MAX
        self.x_axis_labels = GridLayout(
            cols=5, size_hint=(1, None), height=dp_scaled(18),
            pos_hint={'x': 0, 'y': 0.005}, padding=[dp_scaled(12), 0]
        )
        self.labels_list = []
        for _ in range(5):
            lbl = Label(text="", font_size=sp_scaled(15), color=(1, 1, 1, 0.4), bold=True, halign="center")
            self.labels_list.append(lbl)
            self.x_axis_labels.add_widget(lbl)
        
        self.graph_container.add_widget(self.x_axis_labels)
        self.add_widget(self.graph_container)

    def _upd_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def _upd_mesh(self, *args):
        """Berechnet die Füllfläche als sauberes Band exakt unter der Linie."""
        if not self.plot.points:
            self.mesh.vertices = []
            return

        g_pos = self.graph.pos
        g_size = self.graph.size
        
        pad = dp_scaled(0)
        plot_w = g_size[0] - 2 * pad
        plot_h = g_size[1] - 2 * pad
        
        x_min, x_max = self.graph.xmin, self.graph.xmax
        y_min, y_max = self.graph.ymin, self.graph.ymax
        
        x_range = (x_max - x_min) if x_max != x_min else 1
        y_range = (y_max - y_min) if y_max != y_min else 1

        vertices = []
        y_bottom_px = g_pos[1] + pad

        # Wir bauen ein vertikales Band von links nach rechts
        for pt in self.plot.points:
            # Berechne X und Y Pixel-Position des Kurvenpunkts
            px_x = g_pos[0] + pad + ((pt[0] - x_min) / x_range) * plot_w
            px_y = g_pos[1] + pad + ((pt[1] - y_min) / y_range) * plot_h
            
            # 1. Punkt: Auf der Null-Linie (Boden) des aktuellen X-Werts
            vertices.extend([px_x, y_bottom_px, 0, 0])
            # 2. Punkt: Auf der Kurve des aktuellen X-Werts
            vertices.extend([px_x, px_y, 0, 0])

        self.mesh.vertices = vertices
        # Indizes einfach fortlaufend generieren (0, 1, 2, 3...)
        self.mesh.indices = list(range(len(vertices) // 4))

    def update(self, value, buf_key, render=False):
        if value is not None:
            GLOBAL_STATE.graph_engine.process_new_value(buf_key, value)
    
        if not render:
            return
    
        history = GLOBAL_STATE.get_graph_data(buf_key)
        unit = GLOBAL_STATE.get_unit(buf_key)
    
        if not history:
            self.lbl_main_info.text = f"[color=#555555]{self.title}: --[/color]"
            self._render_empty_graph()
            return
    
        last_val = history[-1]
        trend_icon = GLOBAL_STATE.get_trend_icon(buf_key)
    
        if last_val != self._last_val:
            self.lbl_main_info.text = UIFormatter.format_sensor_label(
                name=self.title, value=last_val, unit=unit, trend=trend_icon,
                sz_val=26, sz_name=13, sz_trend=18, sz_unit=13
            )
            self._last_val = last_val
    
        self._render_buffer(history, unit, buf_key)
        self._upd_mesh()

    def _render_empty_graph(self):
        self.plot.points = []
        self.mesh.vertices = []
        self.lbl_avg.text = "avg: ---"
        self.lbl_min.text = "min: ---"
        self.lbl_max.text = "max: ---"
        self.graph.ymin = 0
        self.graph.ymax = 1
        if hasattr(self, 'labels_list'):
            for lbl in self.labels_list:
                lbl.text = ""

    def _render_buffer(self, buf, unit, buf_key):
        if not buf or len(buf) < 2: 
            self._render_empty_graph()
            return
    
        display_buf = list(buf)[-self.window:]
        self.graph.xmin = 0
        self.graph.xmax = max(len(display_buf) - 1, 1)
    
        mn_val = min(display_buf)
        mx_val = max(display_buf)
        
        if mn_val == mx_val:
            self.graph.ymin = mn_val - 1.0
            self.graph.ymax = mx_val + 1.0
        else:
            diff = mx_val - mn_val
            self.graph.ymin = mn_val - (diff * 0.08) 
            self.graph.ymax = mx_val + (diff * 0.08)
    
        self.plot.points = [(i, val) for i, val in enumerate(display_buf)]
        
        # DYNAMISCHE ZEITACHSEN-BERECHNUNG (DEZENT)
        refresh_rate = config.get_refresh_interval()
        total_seconds = len(display_buf) * refresh_rate
        total_minutes = total_seconds / 60

        if hasattr(self, 'labels_list'):
            for i, lbl in enumerate(self.labels_list):
                time_val = -total_minutes + (i * (total_minutes / 4))
                if time_val == 0:
                    lbl.text = "Now"
                elif total_minutes < 1.0:
                    lbl.text = f"{int(time_val * 60)}s"
                else:
                    lbl.text = f"{time_val:.1f}m" if abs(time_val) < 5 else f"{int(time_val)}m"
    
        avg_v, mn_stat, mx_stat = GLOBAL_STATE.graph_engine.get_stats(buf_key)
        if avg_v is not None:
            self.lbl_avg.text = f"avg: {avg_v:.2f} {unit}"
            self.lbl_min.text = f"min: {mn_stat:.2f}{unit}"
            self.lbl_max.text = f"max: {mx_stat:.2f}{unit}"


    def reset(self):
        self.lbl_main_info.text = f"[color=#555555]{self.title}[/color]"
        self._render_empty_graph()

    def on_release(self):
        idx = GLOBAL_STATE.get_active_index()
        dev_list = GLOBAL_STATE.get_device_list()
        if not dev_list or idx >= len(dev_list): return
        item = dev_list[idx]
        dev_id = item.get("device_id") if isinstance(item, dict) else item
        channel = GLOBAL_STATE.get_active_channel()
        full_key = f"{dev_id}_{channel}_{self.tile_id}"
        if hasattr(GLOBAL_STATE, "ggm"):
            GLOBAL_STATE.ggm.engines["dashboard"].open_fullscreen(full_key)