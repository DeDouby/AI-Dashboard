import time
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import Screen
from kivy_garden.graph import Graph, LinePlot
from kivy.graphics import Rectangle, Color
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.metrics import dp
import config 
from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.common.control_buttons import ControlButtons
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled

import os

class FullScreenView(Screen):
    name = "fullscreen"

    def __init__(self, **kw):
        super().__init__(**kw)
        self.tile_id = None
        self.current_key = None
        self._active_unit = ""

        self.layout = FloatLayout()
        self.add_widget(self.layout)
        self.xmax=config.get_tile_graph_window(), # Das Fenster aus der Config
        

        # HINTERGRUND
        with self.layout.canvas.before:
            self.bg_color = Color(0, 0, 0, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size, source="")
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        # GRAPH
        win_seconds = config.get_tile_graph_window()
        self.graph = Graph(
            xmin=0, xmax=win_seconds,
            ymin=0, ymax=1,
            draw_border=False,
            background_color=(0, 0, 0, 0),
            y_grid_label=True,
            x_grid_label=False,
            padding=0,
            label_options={'color':[1,1,1,0.4],'bold':True},
            size_hint=(1,1),
            pos_hint={'x':0,'y':0}
        )
        self.plot = LinePlot(line_width=dp_scaled(4.5))
        self.plot_glow = LinePlot(line_width=dp_scaled(8))
        self.graph.add_plot(self.plot_glow)
        self.graph.add_plot(self.plot)
        self.layout.add_widget(self.graph)

        # X-ACHSE LABELS
        self.x_axis_labels = GridLayout(
            cols=5, size_hint=(1,None), height=dp_scaled(20),
            pos_hint={'x':0,'y':0.08}
        )
        self.labels_list = []
        for _ in range(5):
            lbl = Label(text="", font_size=sp_scaled(11), color=(1,1,1,0.5))
            self.labels_list.append(lbl)
            self.x_axis_labels.add_widget(lbl)
        self.layout.add_widget(self.x_axis_labels)

        # VALUE HUD
        self.hud = BoxLayout(
            orientation="vertical", size_hint=(1,None), height=dp_scaled(180),
            pos_hint={'center_x':0.5,'top':0.85}, spacing=dp_scaled(-10)
        )
        self.lbl_value = Label(
            text="--", font_size=sp_scaled(80), bold=True, markup=True,
            outline_width=2, outline_color=(0,0,0,1)
        )
        self.lbl_sub = Label(
            text="avg: -- | min: -- | max: --", font_size=sp_scaled(18),
            color=(0.8,0.8,0.8,0.8), outline_width=1, outline_color=(0,0,0,1)
        )
        self.hud.add_widget(self.lbl_value)
        self.hud.add_widget(self.lbl_sub)
        self.layout.add_widget(self.hud)

        # HEADER
        self.header = HeaderBar()
        self.header.pos_hint = {'top':1}
        self.layout.add_widget(self.header)
        self.header.update_back_button("fullscreen")

        # NAV BUTTONS
        btn_size = dp_scaled(45)
        self.btn_left = Button(
            text="[font=FA]\uf060[/font]", markup=True, font_size=sp_scaled(20),
            size_hint=(None,None), size=(btn_size,btn_size),
            pos_hint={"x":0.02,"center_y":0.5}, background_color=(0,0,0,0.4)
        )
        self.btn_left.bind(on_release=lambda *_: self._switch(-1))
        self.btn_right = Button(
            text="[font=FA]\uf061[/font]", markup=True, font_size=sp_scaled(20),
            size_hint=(None,None), size=(btn_size,btn_size),
            pos_hint={"right":0.98,"center_y":0.5}, background_color=(0,0,0,0.4)
        )
        self.btn_right.bind(on_release=lambda *_: self._switch(1))
        self.layout.add_widget(self.btn_left)
        self.layout.add_widget(self.btn_right)

        # CONTROL BUTTONS
        self.controls = ControlButtons()
        self.controls.size_hint = (1,None)
        self.controls.height = dp_scaled(40)
        self.controls.pos_hint = {'y':0}
        self.layout.add_widget(self.controls)
        self.active_tile = None  # <-- das ist jetzt der aktuelle Tile-Key
        GLOBAL_STATE.ui_handler.attach_screen("fullscreen", self)

    def _update_bg(self, *_):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def _get_metric_config(self, tile_id):
        """Holt Farbe und Hintergrundbild-Pfad für die jeweilige Kachel."""
        # Der Pfad zu deinen Assets
        asset_path = os.path.join("dashboard_gui", "assets", "tiles")
        
        # Deine alten Definitionen
        config_map = {
            "temp_in": {"color": [1, 0.2, 0.2, 1], "bg": "tile_bg_temp_in.png"},
            "hum_in":  {"color": [0.2, 0.6, 1, 1], "bg": "tile_bg_hum_in.png"},
            "vpd_in":  {"color": [1, 0.8, 0.2, 1], "bg": "tile_bg_vpd_in.png"},
            "temp_ex": {"color": [1, 0.4, 0.4, 1], "bg": "tile_bg_temp_out.png"},
            "hum_ex":  {"color": [0.3, 1, 1, 1],   "bg": "tile_bg_hum_out.png"},
            "vpd_ex":  {"color": [0.3, 1, 0.3, 1], "bg": "tile_bg_vpd_out.png"},
        }
        
        # Daten holen oder Fallback auf Weiß/Leer
        c_data = config_map.get(tile_id, {"color": [1, 1, 1, 1], "bg": ""})
        
        main_color = c_data["color"]
        glow_color = [main_color[0], main_color[1], main_color[2], 0.3] # 30% Glow
        full_bg_path = os.path.join(asset_path, c_data["bg"]) if c_data["bg"] else ""
        
        return main_color, glow_color, full_bg_path
    def activate_tile(self, full_key):
        """Wird beim Klick oder Swipe aufgerufen."""
        print(f"[FS] Aktiviere: {full_key}")
        self.current_key = full_key
        
        # Tile-ID extrahieren (z.B. temp_in)
        parts = full_key.split("_")
        self.tile_id = "_".join(parts[2:]) if len(parts) > 2 else full_key
        
        # 1. Metrik-Konfig laden
        main_col, glow_col, bg_path = self._get_metric_config(self.tile_id)
        
        # 2. HINTERGRUND REPARATUR
        if bg_path and os.path.exists(bg_path):
            self.bg_rect.source = bg_path
            # WICHTIG: Farbe auf Weiß mit Alpha setzen, damit das Bild korrekt strahlt
            self.bg_color.rgba = (1, 1, 1, 0.6) # 0.6 für schönen Kontrast zum Graphen
        else:
            self.bg_rect.source = ""
            self.bg_color.rgba = (0, 0, 0, 1) # Fallback auf Schwarz
        
        # 3. Graph-Farben updaten (Plots löschen und neu setzen)
        for p in list(self.graph.plots):
            self.graph.remove_plot(p)
            
        self.plot = LinePlot(color=main_col, line_width=dp_scaled(4.5))
        self.plot_glow = LinePlot(color=glow_col, line_width=dp_scaled(8))
        self.graph.add_plot(self.plot_glow)
        self.graph.add_plot(self.plot)
        
        # 4. Daten laden
        self._load_data()

    def _load_data(self):
        # 1. Den exakten Kontext holen
        dev_id = GLOBAL_STATE.get_active_device_id()
        channel = GLOBAL_STATE.get_active_channel()
        
        if not dev_id or not self.tile_id:
            return

        # 2. Key bauen (muss exakt zum Metrics-Key passen)
        self.current_key = f"{dev_id}_{channel}_{self.tile_id}"
        
        # 3. Buffer aus der Engine holen
        buf = GLOBAL_STATE.graph_engine.get_buffer(self.current_key)
        
        # Sicherheits-Check: Wenn keine Daten da sind
        if not buf or len(buf) == 0:
            self.plot.points = []
            self.plot_glow.points = []
            self.lbl_value.text = "Warte auf Daten..."
            return

        # 4. GRAPH ZEICHNEN
        pts = list(enumerate(buf))
        self.plot.points = pts
        self.plot_glow.points = pts

        # Achsen skalieren (für die Linien)
        mn, mx = min(buf), max(buf)
        if mn == mx: mn -= 1; mx += 1
        diff = mx - mn
        self.graph.ymin = mn - (diff * 0.1)
        self.graph.ymax = mx + (diff * 0.1)
        self.graph.xmax = config.get_tile_graph_window()

        # ---------------------------------------------------------
        # 5. WERTE-ANZEIGE (Hier lag vermutlich der Fehler)
        # ---------------------------------------------------------
        last_val = buf[-1] # Der allerletzte Wert im Buffer
        
        # Einheit und Trend-Icon vom GSM/Engine holen
        unit = GLOBAL_STATE.get_unit(self.current_key) or ""
        trend_icon = GLOBAL_STATE.graph_engine.get_trend_icon(self.current_key)
        
        # WICHTIG: Markup für das Icon verwenden
        icon_markup = f"[font=FA]{trend_icon}[/font]" if trend_icon else ""

        # Das Haupt-Label (Die große Zahl)
        self.lbl_value.text = f"{last_val:.2f} {unit} {icon_markup}"
        
        # Die Sub-Statistiken (Durchschnitt, Min, Max)
        avg_v, mn_stat, mx_stat = GLOBAL_STATE.graph_engine.get_stats(self.current_key)
        if avg_v is not None:
            self.lbl_sub.text = f"avg: {avg_v:.2f} {unit} | min: {mn_stat:.2f} | max: {mx_stat:.2f}"
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
        for widget in self.walk():
            if hasattr(widget,'reset') and callable(widget.reset):
                widget.reset()
        if hasattr(self,'header'):
            self.header.set_clock("--:--")
            self.header.set_rssi(None)
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