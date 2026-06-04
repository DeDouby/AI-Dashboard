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
from dashboard_gui.ui.scaling_utils import dp_scaled, dp_scaled

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

            xmin=0, xmax=win_seconds,
            ymin=0, ymax=1,
            draw_border=False,
            background_color=(0, 0, 0, 0),
            y_grid_label=True,
            x_grid_label=False,
            padding=dp_scaled(10),
            label_options={'color': [1, 1, 1, 0.4], 'bold': True},
            size_hint=(1, 0.96),
            pos_hint={'x': 0, 'y': 0}
        )
        self.plot = LinePlot(line_width=dp_scaled(3.5))  # Leicht optimiert für Fullscreen
        self.plot_glow = LinePlot(line_width=dp_scaled(7))
        self.graph.add_plot(self.plot_glow)
        self.graph.add_plot(self.plot)
        self.layout.add_widget(self.graph)

        # X-ACHSE LABELS Zeitachse wird jetzt dynamisch in activate_tile mit echten Zeitwerten beschriftet
        self.x_axis_labels = GridLayout(
            cols=5, size_hint=(1,None), height=dp_scaled(20),
            
            pos_hint={'x':0,'y':0.08}
        )
        # -------------------------------------------------
        # 3. NEU: TRANSPARENTE FILL-FLÄCHE (Mesh-Engine aus ChartTile)
        # -------------------------------------------------
        with self.graph.canvas.after:
            self.mesh_color = Color(1, 1, 1, 0.25)  # Wird dynamisch in activate_tile angepasst
            self.mesh = Mesh(mode='triangle_strip')
        
        self.graph.bind(pos=self._upd_mesh, size=self._upd_mesh)

        # X-ACHSE LABELS
        self.x_axis_labels = GridLayout(
            cols=5, size_hint=(1, None), height=dp_scaled(40),
            pos_hint={'x': 0, 'y': 0.08}
        )
        self.labels_list = []
        for _ in range(5):
            lbl = Label(text="", font_size=dp_scaled(24), color=(1, 1, 1, 0.5), bold=True, outline_width=1, outline_color=(0, 0, 0, 1)  )
            self.labels_list.append(lbl)
            self.x_axis_labels.add_widget(lbl)
        self.layout.add_widget(self.x_axis_labels)

        # VALUE HUD
        self.hud = BoxLayout(
            orientation="vertical", size_hint=(1, None), height=dp_scaled(280),
            pos_hint={'center_x': 0.5, 'top': 0.85}, spacing=dp_scaled(-10)
        )
        
        self.lbl_title = Label(text="--", font_size=dp_scaled(45), bold=True, color=(1, 1, 1, 0.9), outline_width=1, outline_color=(0, 0, 0, 1))

        self.lbl_value = Label(
            text="--", font_size=dp_scaled(70), bold=True, markup=True,
            outline_width=3, outline_color=(0, 0, 0, 1)
        )
        self.lbl_sub = Label(
            text="avg: -- | min: -- | max: --", font_size=dp_scaled(24), bold=True,
            color=(0.8, 0.8, 0.8, 0.8), outline_width=1, outline_color=(0, 0, 0, 1)
        )
        self.hud.add_widget(self.lbl_title)
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
            text="[font=FA]\uf060[/font]", markup=True, font_size=dp_scaled(20),
            size_hint=(None, None), size=(btn_size, btn_size),
            pos_hint={"x": 0.02, "center_y": 0.5}, background_color=(0, 0, 0, 0.4)
        )
        self.btn_left.bind(on_release=lambda *_: self._switch(-1))
        self.btn_right = Button(
            text="[font=FA]\uf061[/font]", markup=True, font_size=dp_scaled(20),
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
        """Holt 1:1 die Bezeichnungen, Einheiten und Farben aus dem Dashboard-Konzept."""
        # Gedeckte, professionelle Farbwerte (RGBA)
        c_temp = [0.95, 0.55, 0.22, 1]   # Matt-Bernstein
        c_hum  = [0.24, 0.56, 0.78, 1]   # Ruhiges Blau
        c_vpd  = [0.52, 0.38, 0.76, 1]   # Edles Violett
        c_green = [0.22, 0.68, 0.38, 1]  # Smaragdgrün
        c_bat   = [0.85, 0.68, 0.15, 1]  # Mattgelb
        
        # Mapping für einheitliche Beschriftung und Farben
        config_map = {
            # --- INTERNAL ---
            "temp_in": {"name": "Temperature Internal", "unit": "—", "color": c_temp},
            "hum_in":  {"name": "Humidity Internal", "unit": "%", "color": c_hum},
            "vpd_in":  {"name": "VPD Internal", "unit": "kPa", "color": c_vpd},

            # --- EXTERNAL ---
            "temp_ex": {"name": "Temperature External", "unit": "—", "color": c_temp},
            "hum_ex":  {"name": "Humidity External", "unit": "%", "color": c_hum},
            "vpd_ex":  {"name": "VPD External", "unit": "kPa", "color": c_vpd},

            # --- BLE SPS ---
            "ble_temp_sps": {"name": "Bluetooth SPS Temperature", "unit": "—", "color": c_temp},
            "ble_hum_sps":  {"name": "Bluetooth SPS Humidity", "unit": "%", "color": c_hum},
            "ble_vpd_sps":  {"name": "Bluetooth SPS VPD", "unit": "kPa", "color": c_vpd},

            # --- BLE TB2 ---
            "ble_temp_tb2": {"name": "Bluetooth TB2 Temperature", "unit": "—", "color": c_temp},
            "ble_hum_tb2":  {"name": "Bluetooth TB2 Humidity", "unit": "%", "color": c_hum},
            "ble_vpd_tb2":  {"name": "Bluetooth TB2 VPD", "unit": "kPa", "color": c_vpd},

            # --- SPECIALS ---
            "leaf_temp":           {"name": "Leaf Temperature", "unit": "—", "color": c_green},
            "vpd_leaf":            {"name": "VPD Leaf", "unit": "kPa", "color": c_vpd},
            "circulation_fan_rpm": {"name": "Circulation Fan", "unit": "RPM", "color": c_green},
            "exhaust_fan_rpm":     {"name": "Exhaust Fan", "unit": "RPM", "color": c_green},
            "v_bat":               {"name": "Battery", "unit": "V", "color": c_bat},
        }
        
        # Standard-Fallback, falls ein Key nicht existiert
        fallback = {"name": tile_id.replace("_", " ").upper(), "unit": "", "color": [1, 1, 1, 1]}
        cfg = config_map.get(tile_id, fallback)
        
        main_color = cfg["color"]
        glow_color = [main_color[0], main_color[1], main_color[2], 0.3] # 30% Glow
        
        return main_color, glow_color, cfg["name"], cfg["unit"]


    def activate_tile(self, full_key):
        """Wird beim Klick oder Swipe aufgerufen und setzt Titel & Farben einheitlich."""
        print(f"[FS] Aktiviere: {full_key}")
        self.current_key = full_key
        
        parts = full_key.split("_")
        self.tile_id = "_".join(parts[2:]) if len(parts) > 2 else full_key
        # -------------- HEADER AKTUALISIEREN --------------
        if hasattr(GLOBAL_STATE, 'tile_engine'):
            # Nimm active_tiles aus der Engine
            readable_name = self.tile_id.replace("_", " ").title()  # fallback
            # Optional: du könntest hier auch ein Mapping in TileEngine hinterlegen
            # wenn du fancy Names wie "Temp IN" brauchst
            if self.tile_id in GLOBAL_STATE.tile_engine.active_tiles:
                readable_name = self.tile_id.upper() if "vpd" in self.tile_id else self.tile_id.title()
    
            # Header setzen
            # Header setzen
        # 1. Metrik-Konfig aus dem einheitlichen Mapping laden
        main_col, glow_col, clean_title, static_unit = self._get_metric_config(self.tile_id)

        # --- FIX: DYNAMISCHE EINHEIT AUS UNIT_ENGINE HOLEN ---
        if "temp" in self.tile_id:
            # Falls es eine Temperatur ist, hole die global eingestellte Einheit (°C / °F)
            unit = GLOBAL_STATE.unit_engine.get_temp_unit()
        else:
            # Ansonsten die im State hinterlegte Einheit oder das Fallback aus dem Mapping
            unit = GLOBAL_STATE.get_unit(full_key) or static_unit
            
        self._active_unit = unit
        # -----------------------------------------------------
        
        # Titel direkt mit dem sauberen Namen aus dem Mapping beschriften
        self.lbl_title.text = clean_title

        # 2. HINTERGRUND
        bg_path = os.path.join("dashboard_gui", "assets", "background2.png")
        if os.path.exists(bg_path):
            self.bg_rect.source = bg_path
            self.bg_color.rgba = (1, 1, 1, 0.40)
        else:
            self.bg_rect.source = ""
            self.bg_color.rgba = (0.08, 0.08, 0.1, 1)
        
        # 3. Mesh-Farbe (Füllfläche) updaten
        self.mesh_color.rgba = (main_col[0], main_col[1], main_col[2], 0.25)
        
        # 4. Graph-Plots neu erstellen mit den passenden Farben
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

        # 1. Daten exakt wie in ChartTile holen
        buf = GLOBAL_STATE.get_graph_data(self.current_key)
        if not buf or len(buf) < 1:
            # Falls get_graph_data nicht existiert oder leer ist, 
            # Fallback auf get_buffer (liefert die Liste direkt aus der Engine)
            buf = GLOBAL_STATE.graph_engine.get_buffer(self.current_key)

        if not buf or len(buf) < 1:
            # Wenn immer noch leer, leeren Screen rendern
            if hasattr(self, '_render_empty'):
                self._render_empty()
            return

        # 2. DYNAMISCHE EINHEIT DIREKT AUS DEM STATE ABFRAGEN (Der Core-Fix!)
        # Wir fragen exakt die Einheit ab, die auch die GraphEngine im "current_unit" Check sieht.
        unit = GLOBAL_STATE.get_unit(self.current_key)
        
        # Fallback, falls der State (noch) leer liefert, schauen wir in die unit_engine
        if not unit and "temp" in self.tile_id:
            unit = GLOBAL_STATE.unit_engine.get_temp_unit()
            
        self._active_unit = unit or "—"

        # 3. Puffer für Kivy-Graph vorbereiten
        win_size = config.get_tile_graph_window()
        display_buf = list(buf)[-win_size:]

        self.graph.xmin = 0
        self.graph.xmax = max(len(display_buf) - 1, 1)   

        # Zeitachsen-Beschriftung
        refresh_rate = config.get_refresh_interval()
        total_seconds = len(display_buf) * refresh_rate
        total_minutes = total_seconds / 60

        for i, lbl in enumerate(self.labels_list):
            time_val = -total_minutes + (i * (total_minutes / 4))
            if time_val == 0:
                lbl.text = "Now"
            elif total_minutes < 1.0:
                seconds_val = int(time_val * 60)
                lbl.text = f"{seconds_val}s"
            else:
                lbl.text = f"{time_val:.1f}m" if abs(time_val) < 5 else f"{int(time_val)}m"

        # Punkte setzen (Werte kommen sauber aus dem Puffer)
        pts = list(enumerate(display_buf))
        self.plot.points = pts
        self.plot_glow.points = pts

        # Y-Achsen Grenzen berechnen
        mn_val = min(display_buf)
        mx_val = max(display_buf)
        if mn_val == mx_val:
            self.graph.ymin = mn_val - 1.0
            self.graph.ymax = mx_val + 1.0
        else:
            diff = mx_val - mn_val
            self.graph.ymin = mn_val - (diff * 0.08)
            self.graph.ymax = mx_val + (diff * 0.08)

        self._upd_mesh()   

        # 4. Wert & Einheit im Haupt-HUD anzeigen
        last_val = display_buf[-1]
        trend_icon = GLOBAL_STATE.get_trend_icon(self.current_key)
        icon_markup = f" [font=FA]{trend_icon}[/font]" if trend_icon else ""        
        
        self.lbl_value.text = f"{last_val:.2f} [size={int(dp_scaled(30))}]{self._active_unit}[/size]{icon_markup}"

        # 5. Statistiken befüllen (holen die Min/Max/Avg Werte direkt passend zum Puffer)
        avg_v, mn_stat, mx_stat = GLOBAL_STATE.graph_engine.get_stats(self.current_key)
        if avg_v is not None:
            self.lbl_sub.text = f"avg: {avg_v:.2f} {self._active_unit} | min: {mn_stat:.2f} {self._active_unit} | max: {mx_stat:.2f} {self._active_unit}"


    def update_from_global(self, data):
        # 1. Header updaten
        self.header.update_from_global(data)
        
        if not self.tile_id:
            return

        # 2. PLAUZIBILITÄTS-CHECK: Welches Gerät ist jetzt aktiv?
        active_dev = GLOBAL_STATE.get_active_device_id()
        active_ch = GLOBAL_STATE.get_active_channel()
        
        # Erzeuge den Key, wie er für das AKTUELL NEUE Gerät heißen MÜSSTE
        expected_full_key = f"{active_dev}_{active_ch}_{self.tile_id}"
        
        # Holt die erlaubten Kacheln des aktuellen Geräts
        allowed = GLOBAL_STATE.tile_engine.get_active_tiles() 
        
        # Schutzfunktion greift, wenn das aktuelle Kachel-ID beim neuen Gerät nicht existiert
        if self.tile_id not in allowed and allowed:
            fallback_key = GLOBAL_STATE.tile_engine.get_first_tile_key(active_dev, active_ch)
            print(f"[FS] Schutzfunktion! Tile {self.tile_id} nicht erlaubt für neues Gerät. Springe zu: {fallback_key}")
            if fallback_key:
                self.activate_tile(fallback_key)
            return
            
        # Wenn sich nur die Daten geändert haben, aber das Gerät dasselbe blieb:
        # Aktualisiere den Key auf das neue Format, falls sich Geräte-ID/Kanal geändert haben
        if self.current_key != expected_full_key:
            self.current_key = expected_full_key

        # 3. Wenn alles okay ist: Daten frisch in den Graphen laden
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
    






