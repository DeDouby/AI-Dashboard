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
        self._active_unit = ""
        # SWIPE STATE
        self._touch_start_x = None
        self._touch_active = False
        self._swipe_threshold = dp_scaled(60)
        # --- BASIS: FLOAT LAYOUT (Alles stapelbar) ---
        self.layout = FloatLayout()
        self.add_widget(self.layout)

# 1) HINTERGRUND (Jetzt mit Referenz self.bg_color)
        with self.layout.canvas.before:
            self.bg_color = Color(0, 0, 0, 1) # Start auf Schwarz
            self.bg_rect = Rectangle(pos=self.pos, size=self.size, source="")
        
        self.layout.bind(pos=self._update_bg, size=self._update_bg)

        # 2) DER GRAPH (Layer 0 - Ganz unten, füllt alles)
        self.graph = Graph(
            xmin=0, xmax=60, ymin=0, ymax=1,
            draw_border=False,
            background_color=(0, 0, 0, 0),
            y_grid_label=True,
            y_ticks_major=0.5,
            tick_color=(1, 1, 1, 0.1),
            label_options={'color': [1, 1, 1, 0.6]},
            padding=dp_scaled(20),
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0}
        )
        self.plot = LinePlot(line_width=dp_scaled(4.5))
        self.plot_glow = LinePlot(line_width=dp_scaled(8))
        self.graph.add_plot(self.plot_glow)
        self.graph.add_plot(self.plot)
        self.layout.add_widget(self.graph)

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
        self.header.size_hint_y = None
        self.header.height = dp(45)
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
        self.tile_ref = dashboard.content.tile_map.get(tile_id)
        
        if self.tile_ref:
            # 1. Titel & Unit setzen
            self.header.lbl_title.text = tile_id.replace("_", " ").upper()
            self._active_unit = getattr(self.tile_ref, "unit", "")
            
            # 2. Farben aus der Map holen
            main_color, glow_color = self._get_plot_colors_for_tile(tile_id)
            
            # 3. ALTE PLOTS ENTFERNEN (Das löst das "Weiß"-Problem)
            try:
                for p in list(self.graph.plots):
                    self.graph.remove_plot(p)
            except:
                pass
            
            # 4. NEUE PLOTS ERSTELLEN
            self.plot = LinePlot(color=main_color, line_width=dp_scaled(4.5))
            self.plot_glow = LinePlot(color=glow_color, line_width=dp_scaled(8))
            
            self.graph.add_plot(self.plot_glow)
            self.graph.add_plot(self.plot)

            # 5. Skala-Farbe anpassen (Jetzt sicher ohne font_size Bug)
            self.graph.y_grid_label = True
            self.graph.label_options = {'color': [*main_color[:3], 0.8]}
            
            # 6. Hintergrund setzen
            _, bg_path = self._get_metric_config(tile_id) # Pfad-Logik bleibt
            import os
            if bg_path and os.path.exists(bg_path):
                self.bg_color.rgba = (1, 1, 1, 0.5) 
                self.bg_rect.source = bg_path
            else:
                self.bg_color.rgba = (0, 0, 0, 1)
                self.bg_rect.source = ""
            
            self._load_data()

    def _load_data(self):
        # 1. Dashboard und verfügbare Tiles holen
        dashboard = self.manager.get_screen("dashboard")
        active_keys = dashboard.content.get_active_tile_keys()

        # 2. VERFEINERTE LOGIK:
        # Nur wenn es noch Tiles gibt, aber meins nicht mehr dabei ist -> Wechseln
        if active_keys and self.tile_id not in active_keys:
            print(f"[FULLSCREEN] Sensor nicht mehr verfügbar. Wechsele zu {active_keys[0]}")
            self.activate_tile(active_keys[0])
            return

        # 3. DATEN-QUELLE PRÜFEN
        from dashboard_gui.data_buffer import BUFFER
        data = BUFFER.get()
        idx = GLOBAL_STATE.active_index
        
        # Wenn Puffer leer oder Index ungültig -> Bleib hier, zeig Striche
        if not data or idx >= len(data):
            self.lbl_value.text = f"-- {self._active_unit}"
            self.lbl_sub.text = "VERBINDUNG VERLOREN..."
            return

        if not self.tile_ref: return

        # 4. BUFFER-KEY BAUEN
        dev_id = data[idx].get("device_id")
        channel = GLOBAL_STATE.get_active_channel()
        buf_key = f"{dev_id}_{channel}_{self.tile_id}"
        
        buf = self.tile_ref.buffers.get(buf_key, [])
        if len(buf) > FULLSCREEN_MAX: buf = buf[-FULLSCREEN_MAX:]
        
        # 5. GRAPH & HUD UPDATE
        if buf:
            # --- GRAPH UPDATE ---
            pts = [(i, v) for i, v in enumerate(buf)]
            self.plot.points = pts
            self.plot_glow.points = pts
            
            mn, mx = min(buf), max(buf)
            if mn == mx: mn, mx = mn-0.5, mx+0.5
            diff = mx - mn
            
            self.graph.ymin = mn - (diff * 0.1)
            self.graph.ymax = mx + (diff * 0.1)
            self.graph.y_ticks_major = diff / 4 
            self.graph.xmin, self.graph.xmax = 0, len(buf)-1

           # --- TREND LOGIK (DIREKT VOM GSM) ---
            # Wir holen den nackten Code (\uf...) vom GSM mit dem buf_key
            raw_icon = GLOBAL_STATE.get_trend_icon(buf_key)
            
            # Da lbl_value Text UND Icon mischt, wickeln wir hier das Font-Tag drum:
            trend_icon_markup = f"[font=FA]{raw_icon}[/font]"

           # --- HUD UPDATE ---
            val = buf[-1]
            
            # NEU/FIX: Diese Berechnung hat gefehlt!
            avg_v = sum(buf) / len(buf)
            mn = min(buf)
            mx = max(buf)

            # Jetzt zusammenbauen: Wert + Einheit + Trend-Pfeil (Markup ist an!)
            self.lbl_value.text = f"{val:.2f} {self._active_unit} {trend_icon_markup}"
            self.lbl_value.color = self.plot.color
            
            # Jetzt existiert avg_v und der Fehler ist weg:
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

    def update_from_global(self, d):
        self.header.update_from_global(d)
        self._load_data()

    def reset_from_global(self):
        self.plot.points = []
        self.plot_glow.points = []
        self.lbl_value.text = "--"
        self.lbl_sub.text = "avg: -- | min: -- | max: --"

    # GESTEN ENTFERNT (Kivy Standard-Touch reicht für Buttons)