import os
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy_garden.graph import Graph, LinePlot
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Rectangle, Color

from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.global_state_manager import GLOBAL_STATE


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
        self.window = 120
        self.buffer = []
        self._coord_buffers = {}  # NEU: für interne/externe Koordinaten
        self.last_value = None
        self.smoothing = 0.25
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

        self.lbl_title = Label(text=title, font_size=sp_scaled(16))
        self.lbl_trend = Label(text="", font_size=sp_scaled(18), font_name="FA")
        self.lbl_value = Label(text="--", font_size=sp_scaled(18))

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

        self.plot = LinePlot(color=self.color, line_width=2.0)
        self.graph.add_plot(self.plot)

        glow = [self.color[0], self.color[1], self.color[2], 0.25]
        self.plot_glow = LinePlot(color=glow, line_width=5.0)
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

        self.lbl_avg = Label(text="avg: --", font_size=sp_scaled(12))
        self.lbl_minmax = Label(text="", font_size=sp_scaled(12))

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
    # -------------------------------------------------
    # TILE-COMPATIBLE UPDATE
    # -------------------------------------------------
    def update(self, value, buf_key, stream=None, render=False):
        """
        Update eines Tiles (Buffer + Coord)
        value: float oder int
        buf_key: device_id_channel_tile
        stream: dict mit coord, adv/gatt
        render: Label + Graph sofort aktualisieren
        """
    
        if value is None:
            return
    
        # -------------------------
        # UNIT SWITCH DETECT (nur Float-Werte)
        # -------------------------
        if self.unit != self._last_unit:
            for k, b in self.buffers.items():
                for i in range(len(b)):
                    if isinstance(b[i], dict) and "value" in b[i]:
                        # dict Buffer für Coord
                        if self._last_unit == "°C" and self.unit == "°F":
                            b[i]["value"] = (b[i]["value"] * 9 / 5) + 32
                        elif self._last_unit == "°F" and self.unit == "°C":
                            b[i]["value"] = (b[i]["value"] - 32) * 5 / 9
                    else:
                        # alte Float-Buffer
                        if self._last_unit == "°C" and self.unit == "°F":
                            b[i] = (b[i] * 9 / 5) + 32
                        elif self._last_unit == "°F" and self.unit == "°C":
                            b[i] = (b[i] - 32) * 5 / 9
            self._last_unit = self.unit
    
        # -------------------------
        # Buffer initialisieren
        # -------------------------
        if buf_key not in self.buffers:
            self.buffers[buf_key] = []
        buf = self.buffers[buf_key]
    
        # Value glätten
        try:
            v = float(value)
        except:
            return
    
        if not buf:
            smoothed = v
        else:
            last_val = buf[-1]["value"] if isinstance(buf[-1], dict) else buf[-1]
            smoothed = last_val * (1 - self.smoothing) + v * self.smoothing
    
        # Trend anzeigen
        if render and buf:
            last_val = buf[-1]["value"] if isinstance(buf[-1], dict) else buf[-1]
            diff = smoothed - last_val
            if diff > 0.01:
                self.lbl_trend.text = "\uf062"
            elif diff < -0.01:
                self.lbl_trend.text = "\uf063"
            else:
                self.lbl_trend.text = "\uf061"
    
        # Anzeige
        display_value = smoothed
        if self.base_unit == "°C" and self.unit == "°F":
            display_value = (smoothed * 9 / 5) + 32
    
        # -------------------------
        # Coord aus Stream übernehmen
        # -------------------------
        coords = {"internal": {}, "external": {}}
        if stream and "coord" in stream:
            coords["internal"] = stream["coord"].get("internal", {})
            coords["external"] = stream["coord"].get("external", {})
    
        # -------------------------
        # Float Buffer für alte Graphen
        # -------------------------
        buf.append(smoothed)
        if len(buf) > self.window:
            buf.pop(0)
    
        # -------------------------
        # Coord Buffer für Tiles
        # -------------------------
        if not hasattr(self, "_coord_buffers"):
            self._coord_buffers = {}
        if buf_key not in self._coord_buffers:
            self._coord_buffers[buf_key] = []
        coord_buf = self._coord_buffers[buf_key]
        coord_buf.append({"value": smoothed, "coord": coords})
        if len(coord_buf) > self.window:
            coord_buf.pop(0)
    
        # -------------------------
        # Render Label + Graph (nur Floats)
        # -------------------------
        if render:
            self.lbl_value.text = f"{display_value:.2f} {self.unit}"
            self._render_buffer(buf)  # nur Floats
      
    def _render_buffer(self, buf):
        pts = [(i, val) for i, val in enumerate(buf)]
        self.plot.points = pts
        self.plot_glow.points = pts
    
        if len(buf) > 1:
            mn = min(buf)
            mx = max(buf)
            if mn == mx:
                mn -= 0.5
                mx += 0.5
            margin = (mx - mn) * 0.2
            self.graph.ymin = mn - margin
            self.graph.ymax = mx + margin
    
        self.graph.xmax = max(self.window, len(buf))
    
        # Footer
        if len(buf) > 1:
            avg_v = sum(buf) / len(buf)
            mn = min(buf)
            mx = max(buf)
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
