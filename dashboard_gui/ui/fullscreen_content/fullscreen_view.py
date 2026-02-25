# SESSION 37 – FULLSCREEN WITH SWIPE + SWITCH BUTTONS + ANDROID LAYOUT FIX
import time
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import Screen
from kivy_garden.graph import Graph, LinePlot
from kivy.graphics import Rectangle
from kivy.uix.label import Label
from kivy.uix.button import Button

from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.common.control_buttons import ControlButtons
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled

FULLSCREEN_MAX = 2000
class FullScreenView(Screen):

    def __init__(self, **kw):
        super().__init__(**kw)

        self.tile_id = None
        self.tile_ref = None
        self._touch_start_x = None
        self._zoom = 1.0
        self._view_offset = 0      # wie viele Samples wir von "jetzt" nach links gehen
        self._view_size = 60    # sichtbare Samples (Start wie Tile)
        self._last_tap_time = 0
        self._last_tap_pos = None


        root = BoxLayout(orientation="vertical", spacing=dp_scaled(2), padding=dp_scaled(2))
        self.add_widget(root)

        # BG
        with self.canvas.before:
            self.bg_rect = Rectangle(source="", pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        # HEADER
        self.header = HeaderBar()
        root.add_widget(self.header)
        self.header.update_back_button("fullscreen")
        self.header.set_rssi("--")
        self.header.set_external(False)
        self.header.set_clock("--:--")

    
        # ----------------------------------------------------------
        # GRAPH
        # ----------------------------------------------------------
        self.graph = Graph(
            xlabel="", ylabel="", xmin=0, xmax=60, ymin=0, ymax=1,
            x_ticks_major=0, x_ticks_minor=0,
            y_ticks_major=0, y_ticks_minor=0,
            x_grid_label=False, y_grid_label=False,
            draw_border=False,
            background_color=(0, 0, 0, 0),
            tick_color=(0, 0, 0, 0),
            padding=dp_scaled(2),   # ← EIN Wert, wie im ChartTile
            size_hint=(1, 1),
        )
        
        # Dummy-Plots
        self.plot = LinePlot(color=[1, 1, 1, 1], line_width=3)
        self.graph.add_plot(self.plot)
        self.plot_glow = LinePlot(color=[1, 1, 1, 0.25], line_width=5)
        self.graph.add_plot(self.plot_glow)
        
        root.add_widget(self.graph)
        
        # ----------------------------------------------------------
        # VALUE PANEL – FIXED OVERLAY MIT MITTIGER POSITION
        # ----------------------------------------------------------
        vp_overlay = FloatLayout(
            size_hint=(1, None),
            height=dp_scaled(110),
        )
        root.add_widget(vp_overlay)
        
        # Obere Zeile: Wert + Trend
        row_top = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=dp_scaled(60),
            padding=(dp_scaled(6), 0, dp_scaled(6), 0),
            spacing=dp_scaled(6)
        )
        
        self.lbl_value = Label(
            text="--",
            font_size=sp_scaled(40),
            halign="center",
            valign="middle"
        )
        self.lbl_value.bind(size=self.lbl_value.setter('text_size'))
        
        self.lbl_trend = Label(
            text="→",
            font_size=sp_scaled(34),
            font_name="FA",
            color=(0.7, 0.7, 0.7, 1),
            halign="center",
            valign="middle"
        )
        self.lbl_trend.bind(size=self.lbl_trend.setter('text_size'))
        
        row_top.add_widget(self.lbl_value)
        row_top.add_widget(self.lbl_trend)
        
        # Untere Zeile: Avg / MinMax, horizontal zentriert
        row_bottom = GridLayout(
            cols=2,
            size_hint=(1, None),
            height=dp_scaled(40),
            padding=(dp_scaled(12), 0, dp_scaled(12), dp_scaled(4))
        )
        self.lbl_avg = Label(
            text="avg: --",
            font_size=sp_scaled(14),
            halign="center",
            valign="middle"
        )
        self.lbl_avg.bind(size=self.lbl_avg.setter('text_size'))
        
        self.lbl_minmax = Label(
            text="",
            font_size=sp_scaled(14),
            halign="center",
            valign="middle"
        )
        self.lbl_minmax.bind(size=self.lbl_minmax.setter('text_size'))
        
        row_bottom.add_widget(self.lbl_avg)
        row_bottom.add_widget(self.lbl_minmax)
        
        vp_overlay.add_widget(row_top)
        vp_overlay.add_widget(row_bottom)
        
        row_top.pos_hint = {"top": 1.0}    # Wert oben im Overlay
        row_bottom.pos_hint = {"y": 0.0}   # Avg/MinMax unten
        # ----------------------------------------------------------
        # SWITCH BUTTONS (Session 37C – SAFE OVERLAY)
        # ----------------------------------------------------------
        
        overlay = FloatLayout(size_hint=(1, None), height=0)
        self.add_widget(overlay)  # AUF SCREEN, NICHT im root
        
        btn_size = dp_scaled(42)
        
        self.btn_left = Button(
            text="[font=FA]\uf060[/font]",
            markup=True,
            font_size=sp_scaled(22),
            background_color=(0, 0, 0, 0.28),
            size_hint=(None, None),
            size=(btn_size, btn_size),
            pos_hint={"x": 0.02, "y": 0.45},
            on_release=lambda *_: self._switch(-1)
        )
        
        self.btn_right = Button(
            text="[font=FA]\uf061[/font]",
            markup=True,
            font_size=sp_scaled(22),
            background_color=(0, 0, 0, 0.28),
            size_hint=(None, None),
            size=(btn_size, btn_size),
            pos_hint={"x": 0.92, "y": 0.45},
            on_release=lambda *_: self._switch(+1)
        )
        
        overlay.add_widget(self.btn_left)
        overlay.add_widget(self.btn_right)
        
        # CONTROL BUTTONS
        self.controls = ControlButtons(
            on_start=lambda *_: GLOBAL_STATE.start(),
            on_stop=lambda *_: GLOBAL_STATE.stop(),
            on_reset=lambda *_: GLOBAL_STATE.reset(),
        )
        root.add_widget(self.controls)
        
        GLOBAL_STATE.attach_fullscreen(self)
    # ----------------------------------------------------------
    # COLOR MAP (Double Mapping)
    # ----------------------------------------------------------
    def _get_plot_colors_for_tile(self, tile_id):
        base = {
            "temp_in": [1, 0.2, 0.2, 1],
            "hum_in":  [0.2, 0.6, 1, 1],
            "vpd_in":  [1, 0.8, 0.2, 1],
            "temp_ex": [1, 0.4, 0.4, 1],
            "hum_ex":  [0.3, 1, 1, 1],
            "vpd_ex":  [0.3, 1, 0.3, 1],
        }
        col = base.get(tile_id, [1, 1, 1, 1])
        return [col[0], col[1], col[2], 1], [col[0], col[1], col[2], 0.25]

    # ----------------------------------------------------------
    # TILE SWITCH
    # ----------------------------------------------------------
    def _switch(self, direction):
        dashboard = self.manager.get_screen("dashboard")
        order = dashboard.content.get_active_tile_keys()
    
        if not order or self.tile_id not in order:
            return
    
        idx = order.index(self.tile_id)
        new_idx = (idx + direction) % len(order)
        self.activate_tile(order[new_idx])
    # ----------------------------------------------------------
    # TILE ACTIVATE
    # ----------------------------------------------------------
    def activate_tile(self, tile_id):
        self.tile_id = tile_id

        dashboard = self.manager.get_screen("dashboard")
        tile = dashboard.content.tile_map[tile_id]
        self.tile_ref = tile

        pretty = tile_id.replace("_", " ").title()
        unit = getattr(tile, "unit", "")

        # Header-Titel (einziger Titel!)
        self.header.lbl_title.text = pretty

        # Speichere Unit
        self._active_unit = unit

        self.bg_rect.source = tile.bg_path if getattr(tile, "bg_path", None) else ""

        main_color, glow_color = self._get_plot_colors_for_tile(tile_id)

        try:
            if self.plot in self.graph.plots:
                self.graph.remove_plot(self.plot)
        except:
            pass
        try:
            if self.plot_glow in self.graph.plots:
                self.graph.remove_plot(self.plot_glow)
        except:
            pass

        self.plot = LinePlot(color=main_color, line_width=5.0)
        self.graph.add_plot(self.plot)

        self.plot_glow = LinePlot(color=glow_color, line_width=6)
        self.graph.add_plot(self.plot_glow)

        self._load_tile()

    # ----------------------------------------------------------
    # GRAPH + VALUE UPDATE
    # ----------------------------------------------------------
    def _load_tile(self):
        if not self.tile_ref:
            return

        # --- DEVICE + CHANNEL ERMITTELN ---
        from dashboard_gui.global_state_manager import GLOBAL_STATE
        from dashboard_gui.data_buffer import BUFFER

        data = BUFFER.get()
        if not data or not isinstance(data, list):
            return

        active = GLOBAL_STATE.active_index
        if active >= len(data):
            return

        device_id = data[active].get("device_id")
        if device_id is None:
            return

        # Multi-Channel + Metric Key (Lösung 1)
        active_channel = GLOBAL_STATE.get_active_channel()
        prefix = f"{device_id}_{active_channel}"
        buf_key = f"{prefix}_{self.tile_id}"
        # Unit immer aus dem aktiven Stream ziehen (sonst driftet es bei multi-device)
        try:
            active_frame = data[active]
            stream = active_frame.get(active_channel, {}) or {}
            internal = stream.get("internal", {}) or {}
            external = stream.get("external", {}) or {}
        
            if self.tile_id == "temp_in":
                u = internal.get("temperature", {}).get("unit")
                if u:
                    self._active_unit = u
        
            elif self.tile_id == "temp_ex":
                u = external.get("temperature", {}).get("unit")
                if u:
                    self._active_unit = u
        except:
            pass
        buf = self.tile_ref.buffers.get(buf_key, [])

        # Fullscreen darf mehr Historie sehen
        if len(buf) > FULLSCREEN_MAX:
            buf = buf[-FULLSCREEN_MAX:]
        self._update_graph(buf)
        self._update_panel(buf)

    def _update_graph(self, buf):
        if not buf:
            self.plot.points = []
            self.plot_glow.points = []
            return
    
        total = len(buf)
    
        # --------------------------
        # FULLSCREEN STRETCH
        # --------------------------
        if self.manager.current == "fullscreen" and total > 1:
            # X proportional auf Graph-Breite (0…total-1)
            pts = [(i, v) for i, v in enumerate(buf)]
            self.plot.points = pts
            self.plot_glow.points = pts
    
            # Y-Autoscale
            mn, mx = min(buf), max(buf)
            if mn == mx:
                mn -= 0.5
                mx += 0.5
            margin = (mx - mn) * 0.3
            if mx - mn < 0.1:
                margin = 0.5
            self.graph.ymin = mn - margin
            self.graph.ymax = mx + margin
    
            # X-Achse auf Sichtbereich
            self.graph.xmin = 0
            self.graph.xmax = total - 1  # <- korrekt
            return
    
        # --------------------------
        # NORMALER VIEWPORT (Zoom/Scroll)
        # --------------------------
        view_size = int(self._view_size / self._zoom)
        view_size = max(10, min(view_size, total))
    
        max_offset = max(0, total - view_size)
        self._view_offset = max(0, min(self._view_offset, max_offset))
    
        start = total - view_size - self._view_offset
        end = total - self._view_offset
        view = buf[start:end]
    
        pts = [(i, v) for i, v in enumerate(view)]
        self.plot.points = pts
        self.plot_glow.points = pts
    
        # Y-Autoscale
        mn, mx = min(view), max(view)
        if mn == mx:
            mn -= 0.5
            mx += 0.5
    
        dynamic = max(0.1, 0.5 / self._zoom)
        margin = (mx - mn) * dynamic
        if mx - mn < 0.1:
            margin = 0.5
        self.graph.ymin = mn - margin
        self.graph.ymax = mx + margin

    def _update_panel(self, buf):
        if not buf:
            self.lbl_value.text = "--"
            self.lbl_trend.text = "→"
            self.lbl_avg.text = "avg: --"
            self.lbl_minmax.text = ""
            return

        last = buf[-1]
        self.lbl_value.text = f"{last:.2f} {self._active_unit}"

        if len(buf) > 1:
            diff = last - buf[-2]
            if diff > 0.01:
                self.lbl_trend.text = "\uf062"
            elif diff < -0.01:
                self.lbl_trend.text = "\uf063"
            else:
                self.lbl_trend.text = "\uf061"
        else:
            self.lbl_trend.text = "\uf061"

        avg_v = sum(buf) / len(buf)
        mn, mx = min(buf), max(buf)
        self.lbl_avg.text = f"avg: {avg_v:.2f}"
        self.lbl_minmax.text = f"min: {mn:.2f}   max: {mx:.2f}"

    # ----------------------------------------------------------
    # SWIPE
    # ----------------------------------------------------------
    def on_touch_down(self, touch):
        now = time.time()
    
        # Double-Tap erkennen
        if self._last_tap_time and (now - self._last_tap_time) < 0.35:
            if self._last_tap_pos:
                dx = abs(touch.x - self._last_tap_pos[0])
                dy = abs(touch.y - self._last_tap_pos[1])
    
                # kleiner Bewegungsradius → echter Doppeltap
                if dx < dp_scaled(20) and dy < dp_scaled(20):
                    self._reset_view()
                    self._last_tap_time = 0
                    self._last_tap_pos = None
                    return True
    
        self._last_tap_time = now
        self._last_tap_pos = (touch.x, touch.y)
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        self._touch_start_x = None
        return super().on_touch_up(touch)

    def on_touch_move(self, touch):
        # Vertikal = Zoom
        if abs(touch.dy) > abs(touch.dx):
            self._zoom *= 1.0 + (touch.dy / 600.0)
            self._zoom = max(0.5, min(self._zoom, 5.0))
            self._load_tile()
            return True
    
        # Horizontal = Zeit scrubben
        if abs(touch.dx) > abs(touch.dy):
            self._view_offset += int(touch.dx / 10)
            self._view_offset = max(0, self._view_offset)
            self._load_tile()
            return True
    
        return super().on_touch_move(touch)
    def _reset_view(self):
        self._zoom = 1.0
        self._view_offset = 0
        self._load_tile()
    # ----------------------------------------------------------
    # LIVE UPDATE
    # ----------------------------------------------------------
    def update_from_global(self, d):
        self.header.update_from_global(d)
        # Graph + Werte aktualisieren
        self._load_tile()

    def reset_from_global(self):
        self.plot.points = []
        self.plot_glow.points = []
        self.graph.ymin = 0
        self.graph.ymax = 1
        self.lbl_value.text = "--"
        self.lbl_trend.text = "→"
        self.lbl_avg.text = "avg: --"
        self.lbl_minmax.text = ""
        self._zoom = 1.0
        print("[FULLSCREEN] reset_from_global executed")

    def _update_bg(self, *_):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def back_to_dashboard(self, *_):
        self.manager.current = "dashboard"
