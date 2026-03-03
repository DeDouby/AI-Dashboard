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
        self._touch_start_x = None
        self._touch_active = False
        self._swipe_threshold = dp_scaled(60)

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

        GLOBAL_STATE.ui_handler.attach_screen("fullscreen", self)

    def _update_bg(self, *_):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def _get_plot_colors_for_tile(self, tile_id):
        """Liefert die Hauptfarbe und die Glow-Farbe basierend auf der Metrik-ID."""
        base = {
            "temp_in": [1, 0.2, 0.2, 1],
            "hum_in":  [0.2, 0.6, 1, 1],
            "vpd_in":  [1, 0.8, 0.2, 1],
            "temp_ex": [1, 0.4, 0.4, 1],
            "hum_ex":  [0.3, 1, 1, 1],
            "vpd_ex":  [0.3, 1, 0.3, 1],
        }
        # Fallback auf Weiß, falls die ID nicht in der Liste ist
        col = base.get(tile_id, [1, 1, 1, 1])
        
        # Gibt [Main-Farbe], [Glow-Farbe mit 30% Deckkraft] zurück
        return col, [col[0], col[1], col[2], 0.3]
    def activate_tile(self, full_key):
        """Wird beim Klick auf ein Tile aufgerufen (mit dem langen Key)."""
        print(f"[FS] Aktiviere: {full_key}")
        self.current_key = full_key
        
        # Tile-ID extrahieren für Styling (Farben/Hintergrund)
        # MAC_adv_temp_in -> temp_in
        parts = full_key.split("_")
        self.tile_id = "_".join(parts[2:]) if len(parts) > 2 else full_key
        
        # 1. UI Setup (Farben aus deiner Config holen)
        main_color, glow_color = self._get_plot_colors_for_tile(self.tile_id)
        
        # Plots zurücksetzen
        for p in list(self.graph.plots):
            self.graph.remove_plot(p)
            
        self.plot = LinePlot(color=main_color, line_width=dp_scaled(4.5))
        self.plot_glow = LinePlot(color=glow_color, line_width=dp_scaled(8))
        self.graph.add_plot(self.plot_glow)
        self.graph.add_plot(self.plot)
        
        # 2. Daten sofort einmal laden
        self._load_data()

    def _load_data(self):
        """Holt die Daten direkt aus der GraphEngine."""
        if not hasattr(self, "current_key") or not self.current_key:
            return

        # ZUGRIFF AUF DEINE ENGINE
        # Wir nutzen die Methode get_buffer(), die du oben definiert hast!
        buf = GLOBAL_STATE.graph_engine.get_buffer(self.current_key)
        
        if not buf:
            self.plot.points = []
            self.lbl_value.text = "--"
            return

        # Punkte setzen
        pts = list(enumerate(buf))
        self.plot.points = pts
        self.plot_glow.points = pts

        # Skalierung (Idiotensicher)
        self.graph.xmin = 0
        self.graph.xmax = len(buf) - 1 if len(buf) > 1 else 1
        
        mn, mx = min(buf), max(buf)
        if mn == mx:
            mn -= 0.5; mx += 0.5
        diff = mx - mn
        self.graph.ymin = mn - diff * 0.1
        self.graph.ymax = mx + diff * 0.1

        # Texte
        unit = GLOBAL_STATE.get_unit(self.current_key)
        trend = GLOBAL_STATE.graph_engine.get_trend_icon(self.current_key)
        self.lbl_value.text = f"{buf[-1]:.2f} {unit} [font=FA]{trend}[/font]"
        self.lbl_value.markup = True
    def update_from_global(self, data):
        self.header.update_from_global(data)
        self._load_data()
        win_sec = config.get_tile_graph_window()
        self.graph.xmax = win_sec
        total_min = win_sec / 60
        for i,lbl in enumerate(self.labels_list):
            min_val = (4-i)*(total_min/4)
            lbl.text = "jetzt" if min_val==0 else f"-{int(min_val)}m"

    def _switch(self, direction):
        dashboard = self.manager.get_screen("dashboard")
        order = dashboard.content.get_active_tile_keys()
        if not order or self.tile_id not in order:
            return
        idx = order.index(self.tile_id)
        new_idx = (idx+direction)%len(order)
        self.activate_tile(order[new_idx])

    def reset_from_global(self):
        for widget in self.walk():
            if hasattr(widget,'reset') and callable(widget.reset):
                widget.reset()
        if hasattr(self,'header'):
            self.header.set_clock("--:--")
            self.header.set_rssi(None)

    # Touch-Swipe
    def on_touch_down(self,touch):
        if self.collide_point(*touch.pos):
            self._touch_start_x = touch.x
            self._touch_active = True
        return super().on_touch_down(touch)

    def on_touch_move(self,touch):
        if not self._touch_active or self._touch_start_x is None:
            return super().on_touch_move(touch)
        dx = touch.x - self._touch_start_x
        if abs(dx)>=self._swipe_threshold:
            self._switch(1 if dx<0 else -1)
            self._touch_active = False
            self._touch_start_x = None
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self,touch):
        self._touch_active = False
        self._touch_start_x = None
        return super().on_touch_up(touch)