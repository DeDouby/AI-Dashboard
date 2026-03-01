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
from dashboard_gui.data_buffer import BUFFER

FULLSCREEN_MAX = 2000

class FullScreenView(Screen):
    name = "fullscreen"
    def __init__(self, **kw):
        super().__init__(**kw)
        
        self.tile_id = None
        self._active_unit = ""
        # SWIPE STATE
        self._touch_start_x = None
        self._touch_active = False
        self._swipe_threshold = dp_scaled(60)
        # --- BASIS: FLOAT LAYOUT (Alles stapelbar) ---
        self.layout = FloatLayout()
        self.add_widget(self.layout)
        data = BUFFER.get()
        # 1) HINTERGRUND (Jetzt mit Referenz self.bg_color)
        with self.layout.canvas.before:
            self.bg_color = Color(0, 0, 0, 1) # Start auf Schwarz
            self.bg_rect = Rectangle(pos=self.pos, size=self.size, source="")
        
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        # 2) DER GRAPH (Jetzt Platz-optimiert)
        win_seconds = config.get_tile_graph_window()

        self.graph = Graph(
            xmin=0, xmax=win_seconds, 
            ymin=0, ymax=1,
            draw_border=False,
            background_color=(0, 0, 0, 0),
            y_grid_label=True,      # Y-Werte (z.B. 25°C) bleiben an
            x_grid_label=False,     # X-Werte (Standard) AUS
            y_ticks_major=0.5,
            x_ticks_major=win_seconds / 4, # Raster alle 25%
            padding=0,              # <--- Nimmt den Platz weg! Auf 0 setzen
            label_options={
                'color': [1, 1, 1, 0.4], # 40% Sichtbarkeit (durchscheinend)
                'bold': True
            },
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0}
        )
        self.plot = LinePlot(line_width=dp_scaled(4.5))
        self.plot_glow = LinePlot(line_width=dp_scaled(8))
        self.graph.add_plot(self.plot_glow)
        self.graph.add_plot(self.plot)
        self.layout.add_widget(self.graph)
        
        # Ein Layout für die X-Achsen Beschriftung
        self.x_axis_labels = GridLayout(
            cols=5, # Wir nehmen 5 Punkte (Anfang, 25%, 50%, 75%, Ende)
            size_hint=(1, None),
            height=dp_scaled(20),
            pos_hint={'x': 0, 'y': 0.08} # Position über den Buttons
        )
        
        self.labels_list = []
        for _ in range(5):
            lbl = Label(text="", font_size=sp_scaled(11), color=(1,1,1,0.5))
            self.labels_list.append(lbl)
            self.x_axis_labels.add_widget(lbl)
            
        self.layout.add_widget(self.x_axis_labels)
        # 3) VALUE HUD (Layer 1 - Mittig schwebend)
        self.hud = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            height=dp_scaled(180),
            pos_hint={'center_x': 0.5, 'top': 0.85},
            spacing=dp_scaled(-10)
        )
        # Im Bereich HUD (Punkt 3 der __init__):
        self.lbl_value = Label(
            text="--", 
            font_size=sp_scaled(80), 
            bold=True,
            markup=True,  # <--- SEHR WICHTIG
            outline_width=2, 
            outline_color=(0,0,0,1)
        )
        self.lbl_sub = Label(
            text="avg: -- | min: -- | max: --", font_size=sp_scaled(18),
            color=(0.8, 0.8, 0.8, 0.8), outline_width=1, outline_color=(0,0,0,1)
        )
        self.hud.add_widget(self.lbl_value)
        self.hud.add_widget(self.lbl_sub)
        self.layout.add_widget(self.hud)

        # 4) HEADER (Layer 2 - Oben fest)
        self.header = HeaderBar()
        self.header.pos_hint = {'top': 1}
        self.layout.add_widget(self.header)
        self.header.update_back_button("fullscreen")

        # 5) NAV-BUTTONS (Layer 3 - Links/Rechts schwebend)
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

        # 6) CONTROL BUTTONS (Layer 4 - Unten fest)
        self.controls = ControlButtons(
            on_start=lambda *_: GLOBAL_STATE.start(),
            on_stop=lambda *_: GLOBAL_STATE.stop(),
            on_reset=lambda *_: GLOBAL_STATE.reset(),
        )
        self.controls.size_hint = (1, None)
        self.controls.height = dp_scaled(40)
        self.controls.pos_hint = {'y': 0}
        self.layout.add_widget(self.controls)

        GLOBAL_STATE.attach_fullscreen(self)


    def _update_bg(self, *_):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def _get_metric_config(self, tile_id):
        """Absolut korrekte Pfade mit dem /tiles/ Unterordner"""
        import os
        # Der Pfad geht jetzt tief bis in den tiles-Ordner
        asset_path = os.path.join("dashboard_gui", "assets", "tiles")
        
        config = {
            "temp_in": {"color": [1, 0.2, 0.2], "bg": "tile_bg_temp_in.png"},
            "hum_in":  {"color": [0.2, 0.6, 1], "bg": "tile_bg_hum_in.png"},
            "vpd_in":  {"color": [1, 0.8, 0.2], "bg": "tile_bg_vpd_in.png"},
            "temp_ex": {"color": [1, 0.4, 0.4], "bg": "tile_bg_temp_out.png"},
            "hum_ex":  {"color": [0.3, 1, 1],   "bg": "tile_bg_hum_out.png"},
            "vpd_ex":  {"color": [0.3, 1, 0.3], "bg": "tile_bg_vpd_out.png"},
        }
        
        c_data = config.get(tile_id, {"color": [1, 1, 1], "bg": ""})
        full_bg_path = os.path.join(asset_path, c_data["bg"]) if c_data["bg"] else ""
        
        return c_data["color"], full_bg_path

    def _switch(self, direction):
        # Dashboard-Screen holen
        dashboard = self.manager.get_screen("dashboard")
        
        # Deine Methode nutzen: Nur existierende Tiles in die Liste
        order = dashboard.content.get_active_tile_keys()
    
        if not order or self.tile_id not in order:
            return
    
        # Position finden und rotieren
        idx = order.index(self.tile_id)
        new_idx = (idx + direction) % len(order)
        
        # Umschalten
        self.activate_tile(order[new_idx])

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
        # Gibt [Main-Farbe], [Glow-Farbe] zurück
        return [col[0], col[1], col[2], 1], [col[0], col[1], col[2], 0.3]

    def activate_tile(self, tile_id):
        self.tile_id = tile_id
        dashboard = self.manager.get_screen("dashboard")
        tile = dashboard.content.tile_map.get(tile_id)
    
        if not tile:
            self._active_unit = ""
            return
    
        # DEVICE + CHANNEL
        data = GLOBAL_STATE.get_device_list()
        idx = GLOBAL_STATE.active_index
        dev_id = data[idx] if isinstance(data[idx], str) else data[idx].get("device_id")
        channel = GLOBAL_STATE.get_active_channel()
    
        # buf_key korrekt definieren
        buf_key = f"{dev_id}_{channel}_{tile_id}"
        buf = tile.buffers.get(buf_key, [])
    
        # Unit direkt aus decoded.json übernehmen
        last_val = buf[-1] if buf else None
        if isinstance(last_val, dict):
            self._active_unit = last_val.get("unit", "")
        else:
            self._active_unit = getattr(tile, "unit", "") or ""
    
        self.header.lbl_title.text = tile_id.replace("_", " ").upper()
    
        main_color, glow_color = self._get_plot_colors_for_tile(tile_id)
    
        try:
            for p in list(self.graph.plots):
                self.graph.remove_plot(p)
        except:
            pass
    
        self.plot = LinePlot(color=main_color, line_width=dp_scaled(4.5))
        self.plot_glow = LinePlot(color=glow_color, line_width=dp_scaled(8))
    
        self.graph.add_plot(self.plot_glow)
        self.graph.add_plot(self.plot)
    
        self.graph.label_options = {'color': [*main_color[:3], 0.8]}
    
        _, bg_path = self._get_metric_config(tile_id)
        import os
        if bg_path and os.path.exists(bg_path):
            self.bg_color.rgba = (1, 1, 1, 0.5)
            self.bg_rect.source = bg_path
        else:
            self.bg_color.rgba = (0, 0, 0, 1)
            self.bg_rect.source = ""
    
        self._load_data()

    def _load_data(self):
        from dashboard_gui.data_buffer import BUFFER
        
        # 1. Woher kommen die Daten?
        idx = GLOBAL_STATE.active_index
        channel = GLOBAL_STATE.get_active_channel()
        dev_list = GLOBAL_STATE.get_device_list()
        
        if not dev_list or idx >= len(dev_list):
            return

        dev_id = dev_list[idx]
        # Der Key muss exakt so sein wie im GSM gespeichert!
        buf_key = f"{dev_id}_{channel}_{self.tile_id}"
        
        # 2. Daten direkt aus dem neuen GSM Speicher holen

        buf = GLOBAL_STATE.graph_buffers.get(buf_key, [])
        
        # Wenn Buffer leer oder zu kurz für Berechnungen
        if not buf or len(buf) < 2:
            if hasattr(self, 'plot'): self.plot.points = []
            if hasattr(self, 'plot_glow'): self.plot_glow.points = []
            
            # Falls wir gerade resetten, Achsen stabil halten
            self.graph.xmin = 0
            self.graph.xmax = config.get_tile_graph_window() or 1
            return

        # Erst wenn wir Daten haben, die normalen Berechnungen:
        pts = list(enumerate(buf))
        self.plot.points = pts
        self.plot_glow.points = pts
        # ... Rest der Skalierungslogik ...

        mn = min(buf)
        mx = max(buf)
        if mn == mx:
            mn -= 0.5
            mx += 0.5

        diff = mx - mn
        self.graph.ymin = mn - diff * 0.1
        self.graph.ymax = mx + diff * 0.1
        self.graph.y_ticks_major = diff / 4

        # X-Achse: Zeigt genau so viele Punkte wie da sind
        self.graph.xmin = 0
        self.graph.xmax = len(buf) - 1

        # 4. HUD Texte
        val = buf[-1]
        avg_v = sum(buf) / len(buf)
        trend_icon = GLOBAL_STATE.get_trend_icon(buf_key)
        icon_markup = f"[font=FA]{trend_icon}[/font]" if trend_icon else ""

        self.lbl_value.text = f"{val:.2f} {self._active_unit} {icon_markup}"
        self.lbl_value.color = self.plot.color
        self.lbl_sub.text = f"AVG: {avg_v:.2f} | MIN: {mn:.2f} | MAX: {mx:.2f}"

    # ============================================================
    # TILE SWIPE (HORIZONTAL)
    # ============================================================
    def on_touch_down(self, touch):
        # Wir speichern den Startpunkt, wenn der Touch innerhalb des Screens liegt
        if self.collide_point(*touch.pos):
            self._touch_start_x = touch.x
            self._touch_active = True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if not self._touch_active or self._touch_start_x is None:
            return super().on_touch_move(touch)
    
        dx = touch.x - self._touch_start_x
    
        # Wenn die Bewegung den Schwellenwert überschreitet
        if abs(dx) >= self._swipe_threshold:
            # Swipe nach links (dx negativ) -> Nächstes Tile
            if dx < 0:
                self._switch(1)
            # Swipe nach rechts (dx positiv) -> Vorheriges Tile
            else:
                self._switch(-1)
    
            # 🔒 Swipe verbraucht, deaktivieren bis zum nächsten touch_down
            self._touch_active = False
            self._touch_start_x = None
            return True # Event konsumiert
    
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        self._touch_active = False
        self._touch_start_x = None
        return super().on_touch_up(touch)

    def update_from_global(self, data):
        # 1. Header aktualisieren (LEDs, Name etc.)
        self.header.update_from_global(data)
        
        # 2. X-Achse an Config anpassen
        win_sec = config.get_tile_graph_window()
        self.graph.xmax = win_sec
        
        # 3. Daten neu laden und Graph zeichnen
        self._load_data()
        
        # 4. Zeit-Beschriftung (X-Achse) aktualisieren
        total_min = win_sec / 60
        for i, lbl in enumerate(self.labels_list):
            # Berechnet die Minuten rückwärts von Rechts (0) nach Links
            min_val = (4 - i) * (total_min / 4)
            if min_val == 0:
                lbl.text = "jetzt"
            else:
                lbl.text = f"-{int(min_val)}m"

    def reset_from_global(self):
        """Wird aufgerufen, wenn der Reset-Button gedrückt wird."""
        print(f"[UI] Fullscreen Graph Reset for {self.tile_id}")
        
        # 1. Plots leeren
        if hasattr(self, 'plot'):
            self.plot.points = []
        if hasattr(self, 'plot_glow'):
            self.plot_glow.points = []
        
        # 2. Crash-Schutz: X- und Y-Achse auf Minimalwerte setzen
        # xmax darf niemals gleich xmin sein!
        self.graph.xmin = 0
        self.graph.xmax = 1 # Minimaler Abstand verhindert ZeroDivisionError
        self.graph.ymin = 0
        self.graph.ymax = 1
        
        # 3. Texte zurücksetzen
        unit = getattr(self, "_active_unit", "")
        self.lbl_value.text = f"-- {unit}"
        self.lbl_sub.text = "BUFFER GELEERT"
        
        # 4. UI Update triggern (Größenänderung erzwingt Neuzeichnung sicher)
        self.graph._trigger_size()

