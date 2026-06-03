import os
import time
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import Screen
from kivy_garden.graph import Graph, LinePlot
from kivy.graphics import Rectangle, Color, Mesh  # NEU: Mesh importiert
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.metrics import dp
import config 
from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.common.control_buttons import ControlButtons
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled

class FullScreenView(Screen):
    name = "fullscreen"

    def __init__(self, **kw):
        super().__init__(**kw)
        self.tile_id = None
        self.current_key = None
        self._active_unit = ""

        self.layout = FloatLayout()
        self.add_widget(self.layout)
        self.xmax = config.get_tile_graph_window()

        # -------------------------------------------------
        # 1. HINTERGRUND INITIALISIERUNG
        # -------------------------------------------------
        with self.layout.canvas.before:
            # Startet mit dem edlen, abgedunkelten Kachel-Grundton
            self.bg_color = Color(0.08, 0.08, 0.1, 0.40)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size, source="")
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        # -------------------------------------------------
        # 2. GRAPH & PLOTS
        # -------------------------------------------------
        win_seconds = config.get_tile_graph_window()
        # Ersetze den alten Graph-Block durch diesen:
        self.graph = Graph(
            xmin=0, xmax=1,                    # wird später überschrieben
            ymin=0, ymax=1,
            draw_border=False,
            background_color=(0, 0, 0, 0),
            y_grid_label=True,
            x_grid_label=False,
            padding=dp_scaled(10),
            label_options={'color': [1, 1, 1, 0.4], 'bold': True},
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0}
        )
        self.plot = LinePlot(line_width=dp_scaled(3.5))  # Leicht optimiert für Fullscreen
        self.plot_glow = LinePlot(line_width=dp_scaled(7))
        self.graph.add_plot(self.plot_glow)
        self.graph.add_plot(self.plot)
        self.layout.add_widget(self.graph)

        # -------------------------------------------------
        # 3. NEU: TRANSPARENTE FILL-FLÄCHE (Mesh-Engine aus ChartTile)
        # -------------------------------------------------
        with self.graph.canvas.after:
            self.mesh_color = Color(1, 1, 1, 0.25)  # Wird dynamisch in activate_tile angepasst
            self.mesh = Mesh(mode='triangle_strip')
        
        self.graph.bind(pos=self._upd_mesh, size=self._upd_mesh)

        # X-ACHSE LABELS
        self.x_axis_labels = GridLayout(
            cols=5, size_hint=(1, None), height=dp_scaled(20),
            pos_hint={'x': 0, 'y': 0.08}
        )
        self.labels_list = []
        for _ in range(5):
            lbl = Label(text="", font_size=sp_scaled(16), color=(1, 1, 1, 0.5))
            self.labels_list.append(lbl)
            self.x_axis_labels.add_widget(lbl)
        self.layout.add_widget(self.x_axis_labels)

        # VALUE HUD
        self.hud = BoxLayout(
            orientation="vertical", size_hint=(1, None), height=dp_scaled(180),
            pos_hint={'center_x': 0.5, 'top': 0.85}, spacing=dp_scaled(-10)
        )
        self.lbl_value = Label(
            text="--", font_size=sp_scaled(80), bold=True, markup=True,
            outline_width=2, outline_color=(0, 0, 0, 1)
        )
        self.lbl_sub = Label(
            text="avg: -- | min: -- | max: --", font_size=sp_scaled(18),
            color=(0.8, 0.8, 0.8, 0.8), outline_width=1, outline_color=(0, 0, 0, 1)
        )
        self.hud.add_widget(self.lbl_value)
        self.hud.add_widget(self.lbl_sub)
        self.layout.add_widget(self.hud)

        # HEADER
        self.header = HeaderBar()
        self.header.pos_hint = {'top': 1}
        self.layout.add_widget(self.header)

        # NAV BUTTONS
        btn_size = dp_scaled(45)
        self.btn_left = Button(
            text="[font=FA]\uf060[/font]", markup=True, font_size=sp_scaled(20),
            size_hint=(None, None), size=(btn_size, btn_size),
            pos_hint={"x": 0.02, "center_y": 0.5}, background_color=(0, 0, 0, 0.4)
        )
        self.btn_left.bind(on_release=lambda *_: self._switch(-1))
        self.btn_right = Button(
            text="[font=FA]\uf061[/font]", markup=True, font_size=sp_scaled(20),
            size_hint=(None, None), size=(btn_size, btn_size),
            pos_hint={"right": 0.98, "center_y": 0.5}, background_color=(0, 0, 0, 0.4)
        )
        self.btn_right.bind(on_release=lambda *_: self._switch(1))
        self.layout.add_widget(self.btn_left)
        self.layout.add_widget(self.btn_right)

        # CONTROL BUTTONS
        self.controls = ControlButtons(on_reset=self.reset_from_global)
        self.controls.size_hint = (1, None)
        self.controls.height = dp_scaled(40)
        self.controls.pos_hint = {'y': 0}
        self.layout.add_widget(self.controls)
        self.active_tile = None  
        GLOBAL_STATE.ui_handler.attach_screen("fullscreen", self)

    def _update_bg(self, *_):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    # -------------------------------------------------
    # 4. NEU: DYNAMISCHE MESH-BERECHNUNG FÜR FULLSCREEN
    # -------------------------------------------------
    def _upd_mesh(self, *args):
        """Berechnet die Füllfläche exakt unter der Kurvenlinie im Fullscreen."""
        if not hasattr(self, 'plot') or not self.plot.points:
            self.mesh.vertices = []
            return

        g_pos = self.graph.pos
        g_size = self.graph.size
        
        pad = dp_scaled(10)
        plot_w = g_size[0] - 2 * pad
        plot_h = g_size[1] - 2 * pad
        
        x_min, x_max = self.graph.xmin, self.graph.xmax
        y_min, y_max = self.graph.ymin, self.graph.ymax
        
        x_range = (x_max - x_min) if x_max != x_min else 1
        y_range = (y_max - y_min) if y_max != y_min else 1

        vertices = []
        y_bottom_px = g_pos[1] + pad

        for pt in self.plot.points:
            px_x = g_pos[0] + pad + ((pt[0] - x_min) / x_range) * plot_w
            px_y = g_pos[1] + pad + ((pt[1] - y_min) / y_range) * plot_h
            
            # 1. Punkt auf der Null-Linie (Boden)
            vertices.extend([px_x, y_bottom_px, 0, 0])
            # 2. Punkt direkt auf dem Kurvenpunkt
            vertices.extend([px_x, px_y, 0, 0])

        self.mesh.vertices = vertices
        self.mesh.indices = list(range(len(vertices) // 4))

    # -------------------------------------------------
    # 5. ASSIMILIERTE FARB-DEFINITIONEN (1:1 Main Panel)
    # -------------------------------------------------
    def _get_metric_config(self, tile_id):
        """Holt 1:1 die gedeckten, professionellen Farben aus dem DashboardMainPanel."""
        asset_path = os.path.join("dashboard_gui", "assets")
        
        # Exakte Farbwerte aus deinem DashboardMainPanel kopiert
        c_temp = [0.95, 0.55, 0.22, 1]   # Matt-Bernstein
        c_hum  = [0.24, 0.56, 0.78, 1]   # Ruhiges Blau
        c_vpd  = [0.52, 0.38, 0.76, 1]   # Edles Violett
        c_green = [0.22, 0.68, 0.38, 1]  # Smaragdgrün
        c_bat   = [0.85, 0.68, 0.15, 1]  # Mattgelb
        
        config_map = {
            # --- INTERNAL ---
            "temp_in": {"color": c_temp, "bg": "background2.png"},
            "hum_in":  {"color": c_hum,  "bg": "background2.png"},
            "vpd_in":  {"color": c_vpd,  "bg": "background2.png"},

            # --- EXTERNAL 1 ---
            "temp_ex": {"color": c_temp, "bg": "background2.png"},
            "hum_ex":  {"color": c_hum,  "bg": "background2.png"},
            "vpd_ex":  {"color": c_vpd,  "bg": "background2.png"},

            # --- EXTERNAL 2 (LEAF) ---
            "leaf_temp": {"color": c_green, "bg": "background2.png"},
            "vpd_leaf":  {"color": c_vpd,   "bg": "background2.png"},

            # --- BLE SPS ---
            "ble_temp_sps": {"color": c_temp, "bg": "background2.png"},
            "ble_hum_sps":  {"color": c_hum,  "bg": "background2.png"},
            "ble_vpd_sps":  {"color": c_vpd,  "bg": "background2.png"},

            # --- BLE TB2 ---
            "ble_temp_tb2": {"color": c_temp, "bg": "background2.png"},
            "ble_hum_tb2":  {"color": c_hum,  "bg": "background2.png"},
            "ble_vpd_tb2":  {"color": c_vpd,  "bg": "background2.png"},

            # --- MISC (BATT / FANS) ---
            "v_bat":               {"color": c_bat,   "bg": "background2.png"},
            "circulation_fan_rpm": {"color": c_green, "bg": "background2.png"},
            "exhaust_fan_rpm":     {"color": c_green, "bg": "background2.png"},
        }
        
        c_data = config_map.get(tile_id, {"color": [1, 1, 1, 1], "bg": ""})
        
        main_color = c_data["color"]
        glow_color = [main_color[0], main_color[1], main_color[2], 0.3] # 30% Glow für die dicke Linie
        full_bg_path = os.path.join(asset_path, c_data["bg"]) if c_data["bg"] else ""
        
        return main_color, glow_color, full_bg_path

    def activate_tile(self, full_key):
        """Wird beim Klick oder Swipe aufgerufen."""
        print(f"[FS] Aktiviere: {full_key}")
        self.current_key = full_key
        
        parts = full_key.split("_")
        self.tile_id = "_".join(parts[2:]) if len(parts) > 2 else full_key
        
        # 1. Metrik-Konfig laden (jetzt mit den neuen Farben)
        main_col, glow_col, bg_path = self._get_metric_config(self.tile_id)
        
        # 2. HINTERGRUND REPARATUR (An Kachel-Transparenz angepasst)
        if bg_path and os.path.exists(bg_path):
            self.bg_rect.source = bg_path
            # NEU: Alpha auf 0.40 gesenkt für perfekten UI-Glow-Kontrast
            self.bg_color.rgba = (1, 1, 1, 0.40) 
        else:
            self.bg_rect.source = ""
            self.bg_color.rgba = (0.08, 0.08, 0.1, 1) # Fallback auf Kachel-Dunkelblau
        
        # 3. Mesh-Farbe updaten (25% Deckkraft der Linienfarbe analog zur Kachel)
        self.mesh_color.rgba = (main_col[0], main_col[1], main_col[2], 0.25)
        
        # 4. Graph-Farben updaten
        for p in list(self.graph.plots):
            self.graph.remove_plot(p)
            
        self.plot = LinePlot(color=main_col, line_width=dp_scaled(4.5))
        self.plot_glow = LinePlot(color=glow_col, line_width=dp_scaled(8))
        self.graph.add_plot(self.plot_glow)
        self.graph.add_plot(self.plot)
        
        # 5. Daten laden
        self._load_data()

    def _load_data(self):
        if not self.current_key:
            return

        buf = GLOBAL_STATE.graph_engine.get_buffer(self.current_key)
        if not buf or len(buf) < 1:
            self._render_empty()
            return

        win_size = config.get_tile_graph_window()
        display_buf = list(buf)[-win_size:]

        # ←←← DAS IST DER WICHTIGSTE TEIL ←←←
        self.graph.xmin = 0
        self.graph.xmax = max(len(display_buf) - 1, 1)   # Sofort volle Breite

        pts = list(enumerate(display_buf))
        self.plot.points = pts
        self.plot_glow.points = pts

        # Y Skalierung
        mn_val = min(display_buf)
        mx_val = max(display_buf)
        if mn_val == mx_val:
            self.graph.ymin = mn_val - 1.0
            self.graph.ymax = mx_val + 1.0
        else:
            diff = mx_val - mn_val
            self.graph.ymin = mn_val - (diff * 0.08)
            self.graph.ymax = mx_val + (diff * 0.08)

        self._upd_mesh()   # Mesh sofort updaten

        unit = GLOBAL_STATE.get_unit(self.current_key) or ""
        avg_v, mn_stat, mx_stat = GLOBAL_STATE.graph_engine.get_stats(self.current_key)

        self.lbl_value.text = f"{display_buf[-1]:.2f} [size={int(sp_scaled(30))}]{unit}[/size]"
        if avg_v is not None:
            self.lbl_sub.text = f"avg: {avg_v:.2f} {unit} | min: {mn_stat:.2f} {unit} | max: {mx_stat:.2f} {unit}"

    def update_from_global(self, data):
        # 1. Header updaten
        self.header.update_from_global(data)
        
        # 2. PLAUZIBILITÄTS-CHECK: Ist mein aktuelles Tile beim neuen Gerät überhaupt erlaubt?
        allowed = GLOBAL_STATE.tile_engine.get_active_tiles() # Liste z.B. ["temp_in", "hum_in"]
        
        if self.tile_id not in allowed and allowed:
            # Falls nicht: Springe zum ersten verfügbaren Tile des neuen Geräts
            print(f"[FS] Tile {self.tile_id} nicht verfügbar für dieses Gerät. Springe zu {allowed[0]}")
            self.activate_tile(f"{GLOBAL_STATE.get_active_device_id()}_{GLOBAL_STATE.get_active_channel()}_{allowed[0]}")
            return # activate_tile ruft _load_data bereits auf

        # 3. Wenn alles okay ist: Daten laden
        self._load_data()

    def _switch(self, direction):
        """Fragt einfach die TileEngine nach dem nächsten Key."""
        if not self.current_key:
            return

        # Die TileEngine berechnet den Nachbarn basierend auf der Metrics-Wahrheit
        next_key = GLOBAL_STATE.tile_engine.get_next_full_key(self.current_key, direction)
        
        if next_key != self.current_key:
            self.activate_tile(next_key)

    def reset_from_global(self):
        """Löscht alle Anzeigen im Fullscreen-Modus."""
        print("[FS] Resetting Fullscreen UI...")
        
        # 1. Die großen HUD Labels säubern
        unit = GLOBAL_STATE.get_unit(self.current_key) if self.current_key else ""
        self.lbl_value.text = f"--- {unit}"
        self.lbl_sub.text = "avg: --- | min: --- | max: ---"
        
        # 2. Den Graphen leeren
        self.plot.points = []
        self.plot_glow.points = []
        self.graph.ymin = 0
        self.graph.ymax = 1
        
        # 3. Header aufräumen
        if hasattr(self, 'header'):
            self.header.set_rssi(None)
            
        # 4. Falls Unter-Widgets existieren, die reset() können (Sicherheitshalber)
        for widget in self.walk():
            if widget != self and hasattr(widget, 'reset') and callable(widget.reset):
                widget.reset()

# --- TOUCH SWIPE (Idiotensicher fixiert) ---
    # In dashboard_gui/ui/fullscreen_content/fullscreen_view.py
    
    def on_touch_down(self, touch):
        # Wir nutzen den GGM und sagen ihm: "Ich bin der fullscreen screen"
        if hasattr(GLOBAL_STATE, "ggm"):
            GLOBAL_STATE.ggm.handle_touch("fullscreen", "down", touch)
        return super().on_touch_down(touch)
    
    def on_touch_move(self, touch):
        if hasattr(GLOBAL_STATE, "ggm"):
            GLOBAL_STATE.ggm.handle_touch("fullscreen", "move", touch)
        return super().on_touch_move(touch)
    
    def on_touch_up(self, touch):
        if hasattr(GLOBAL_STATE, "ggm"):
            GLOBAL_STATE.ggm.handle_touch("fullscreen", "up", touch)
        return super().on_touch_up(touch)
    






