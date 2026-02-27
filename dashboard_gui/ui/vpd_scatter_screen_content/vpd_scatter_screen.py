from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import Screen
from kivy.graphics import Rectangle, Color, Ellipse
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock
from kivy.app import App
from kivy.metrics import dp
from kivy.uix.label import Label
from kivy.uix.anchorlayout import AnchorLayout
from kivy_garden.graph import Graph
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.common.control_buttons import ControlButtons
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle
import math
import time


class VPDScatterScreen(Screen):


    """
    VPD Scatter – FINAL STABLE VERSION
    - Keine Garden-Plots
    - Punkte via Canvas (Ellipse)
    - Graph nur als Koordinaten-Referenz
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.gsm = GLOBAL_STATE


        # -------------------------------------------------
        # ROOT
        # -------------------------------------------------
        self.main = BoxLayout(orientation="vertical")
        self.add_widget(self.main)
        # -------------------------------------------------
        # VPD BACKGROUND MODES
        # -------------------------------------------------
        self._vpd_bgs = {
            "default": "dashboard_gui/assets/vpd_bg.png",
            "seedling": "dashboard_gui/assets/vpd_bg_seedling.png",
            "veg": "dashboard_gui/assets/vpd_bg_veg.png",
            "flower": "dashboard_gui/assets/vpd_bg_flower.png",
        }

        self._active_bg = "default"

        # -------------------------------------------------
        # HEADER
        # -------------------------------------------------
        app = App.get_running_app()
        sm = app.root if app else None

        self.header = HeaderBar()
        self.header.size_hint_y = None
        self.header.height = dp(45)
        self.main.add_widget(self.header)

        self.header.enable_back("dashboard")
        self.header.update_back_button("vpd_scatter")

        self.gsm.attach_vpd_scatter(self)
        self._reset_active = False

        # -------------------------------------------------
        # CONTENT
        # -------------------------------------------------
        self.content = FloatLayout()

        # -------------------------------------------------
        # BG SWITCH MENU (TOP-LEFT)
        # -------------------------------------------------
        from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
        from kivy.uix.button import Button

        self.bg_menu = BoxLayout(
            orientation="horizontal",
            size_hint=(None, None),
            height=dp_scaled(36),
            spacing=dp_scaled(6),
            pos_hint={"x": 0, "top": 1},
            padding=(dp_scaled(8), dp_scaled(8))
        )

        def mk_bg_btn(txt, key):
            btn = Button(
                text=txt,
                size_hint=(None, None),
                size=(dp_scaled(90), dp_scaled(32)),
                font_size=sp_scaled(14),
                # background_normal leer lassen, damit unsere background_color wirkt
                background_normal='',
                # Standardzustand: 0.45 Alpha
                background_color=(0.05, 0.05, 0.05, 0.45),
                on_release=lambda *_: self._set_vpd_bg(key)
            )
        
            # Feedback-Logik: Beim Drücken wird der Button etwas heller/weniger transparent
            def on_state(instance, value):
                if value == 'down':
                    # Hellerer Zustand beim Drücken (0.7 Alpha)
                    instance.background_color = (0.2, 0.2, 0.2, 0.7)
                else:
                    # Zurück zum HUD-Style (0.45 Alpha)
                    instance.background_color = (0.05, 0.05, 0.05, 0.45)
        
            btn.bind(state=on_state)
            return btn

        self.bg_menu.add_widget(mk_bg_btn("Default", "default"))
        self.bg_menu.add_widget(mk_bg_btn("Seedling", "seedling"))
        self.bg_menu.add_widget(mk_bg_btn("Veg", "veg"))
        self.bg_menu.add_widget(mk_bg_btn("Flower", "flower"))

        self.content.add_widget(self.bg_menu)

        # -------------------------------------------------
        # VALUE MIRROR BOX (RECHTS)
        # -------------------------------------------------
        from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
        
        self.value_box = AnchorLayout(
            anchor_x="right",
            anchor_y="top",
            size_hint=(1, 1),
            padding=(dp_scaled(8), dp_scaled(72), dp_scaled(8), dp_scaled(8))
        )
        
        self.value_label = Label(
            text="",
            size_hint=(0.25, None),   # 🔑 Android-safe, max ~50% Breite
            halign="left",
            valign="middle",
            markup=True,
            font_size=sp_scaled(20),
        )
        
        # 🔑 Auto-Höhe nach Text
        self.value_label.bind(
            size=lambda inst, *_: setattr(inst, "text_size", (inst.width - dp_scaled(16), None)),
            texture_size=lambda inst, *_: setattr(inst, "height", inst.texture_size[1] + dp_scaled(16)),
        )
        
        with self.value_label.canvas.before:
            # Hintergrund – deutlich transparenter
            Color(0.05, 0.05, 0.05, 0.45)
            self._value_bg = RoundedRectangle(radius=[dp_scaled(14)])
        
            # Border – sehr subtil, fast HUD-like
            Color(0.8, 0.8, 0.8, 0.18)
            self._value_border = RoundedRectangle(radius=[dp_scaled(14)], width=1.0)
        
        self.value_label.bind(pos=self._sync_value_box, size=self._sync_value_box)
        
        self.value_box.add_widget(self.value_label)
        self.content.add_widget(self.value_box)
        self.main.add_widget(self.content)
        self._mirror = {
            "in": {"t": None, "h": None, "vpd": None},
            "ex": {"t": None, "h": None, "vpd": None},
        }
        # -------------------------------------------------
        # BACKGROUND (PNG = ACHSEN)
        # -------------------------------------------------
        with self.content.canvas.before:
            self.bg_rect = Rectangle(
                texture=CoreImage(
                    "dashboard_gui/assets/vpd_bg.png"
                ).texture,
                size=self.content.size,
                pos=self.content.pos,
            )
        self.content.bind(size=self._update_bg, pos=self._update_bg)

        # -------------------------------------------------
        # GRAPH (NUR KOORDINATEN!)
        # -------------------------------------------------
        self.graph = Graph(
            xmin=15,   # Humidity %
            xmax=120,
            ymin=10,    # Temperatur °C
            ymax=25,
            draw_border=False,
            background_color=(0, 0, 0, 0),
            tick_color=(0, 0, 0, 0),
            padding=0,
        )
        self.content.add_widget(self.graph)

        self.graph.bind(size=self._sync_graph, pos=self._sync_graph)
        self.content.bind(size=self._sync_graph, pos=self._sync_graph)

        # -------------------------------------------------
        # SCATTER POINTS (CANVAS – DAS IST DER KEY)
        # -------------------------------------------------
        with self.graph.canvas.after:
            # INTERN
            Color(1.0, 0.85, 0.2, 0.85)  # IN
            self.p_in = Ellipse(size=(36, 36), pos=(-1000, -1000))

            # EXTERN
            Color(0.3, 1.0, 0.3, 0.85)  # EX
            self.p_ex = Ellipse(size=(36, 36), pos=(-1000, -1000))

        # -------------------------------------------------
        # CONTROL BUTTONS
        # -------------------------------------------------
        self.controls = ControlButtons(
            on_start=lambda *_: GLOBAL_STATE.start(),
            on_stop=lambda *_: GLOBAL_STATE.stop(),
            on_reset=lambda *_: GLOBAL_STATE.reset(),
        )
        self.main.add_widget(self.controls)

        Clock.schedule_interval(self._tick, 1.0)

        # -------------------------------------------------
        # DEVICE SWIPE (HORIZONTAL) – IDENTISCH ZUM MAINPANEL
        # -------------------------------------------------
        from dashboard_gui.ui.scaling_utils import dp_scaled
        self._touch_start_x = None
        self._touch_active = False
        self._swipe_threshold = dp_scaled(60)


    # -------------------------------------------------
    # LAYOUT SYNC
    # -------------------------------------------------
    def _update_bg(self, *_):
        self.bg_rect.size = self.content.size
        self.bg_rect.pos = self.content.pos

    def _sync_graph(self, *_):
        self.graph.size = self.content.size
        self.graph.pos = self.content.pos

    def _sync_value_box(self, *_):
        self._value_bg.size = self.value_label.size
        self._value_bg.pos = self.value_label.pos
        self._value_border.size = self.value_label.size
        self._value_border.pos = self.value_label.pos
    def _last_float(self, buf):
        if not buf:
            return None
        v = buf[-1]
        return float(v) if v is not None else None    
    def _temp_from_vpd_rh(self, vpd, rh):
        if vpd <= 0 or rh <= 0 or rh >= 100:
            return None
    
        es = vpd / (1.0 - rh / 100.0)
        L = math.log(es / 0.6108)
        return (237.3 * L) / (17.27 - L)
    def _set_vpd_bg(self, key):
        path = self._vpd_bgs.get(key)
        if not path:
            return

        self.bg_rect.texture = CoreImage(path).texture
        self._active_bg = key


    # -------------------------------------------------
    # DATA LOAD (IDENTISCH ZU FULLSCREEN)
    # -------------------------------------------------
    def _load_points(self):
        from dashboard_gui.data_buffer import BUFFER
        import config
    
        # Scatter-relevante Offsets (nur hier!)
        t_off    = float(config.get_temperature_offset() or 0.0)
        leaf_off = float(config.get_leaf_offset() or 0.0)
        self._leaf_offset = leaf_off   # ✅ FIX

        data = BUFFER.get()
        if not data or not isinstance(data, list):
            return
    
        active = self.gsm.active_index
        if active >= len(data):
            return
    
        device_id = data[active].get("device_id")
        if not device_id:
            return
    
        ch = self.gsm.get_active_channel()
        prefix = f"{device_id}_{ch}"

    
        dashboard = self.manager.get_screen("dashboard")
        tiles = dashboard.content.tile_map
    
        tile_vpd_in = tiles.get("vpd_in")
        tile_vpd_ex = tiles.get("vpd_ex")
        tile_h_in   = tiles.get("hum_in")
        tile_h_ex   = tiles.get("hum_ex")
        tile_t_in   = tiles.get("temp_in")
        tile_t_ex   = tiles.get("temp_ex")
    
        if not tile_vpd_in or not tile_vpd_ex:
            self.p_in.pos = (-1000, -1000)
            self.p_ex.pos = (-1000, -1000)
            return
    
        vpd_in = tile_vpd_in.buffers.get(f"{prefix}_vpd_in", [])
        vpd_ex = tile_vpd_ex.buffers.get(f"{prefix}_vpd_ex", [])
        h_in   = tile_h_in.buffers.get(f"{prefix}_hum_in", []) if tile_h_in else []
        h_ex   = tile_h_ex.buffers.get(f"{prefix}_hum_ex", []) if tile_h_ex else []
        # -------------------------
        # IN (Scatter)
        # -------------------------
        if vpd_in and h_in:
            vpd = float(vpd_in[-1])
            rh  = float(h_in[-1])
    
            t_eff = self._temp_from_vpd_rh(vpd, rh)
            if t_eff is not None:
                t_scatter = t_eff + t_off + leaf_off
                self._place_point(self.p_in, t_scatter, rh)
    
                # Mirror nur intern (Scatter/Debug)
                self._mirror["in"] = {"t": t_scatter, "h": rh, "vpd": vpd}
            else:
                self.p_in.pos = (-1000, -1000)
        else:
            self.p_in.pos = (-1000, -1000)
    
        # -------------------------
        # EX (Scatter)
        # -------------------------
        if vpd_ex and h_ex:
            vpd = float(vpd_ex[-1])
            rh  = float(h_ex[-1])
    
            t_eff = self._temp_from_vpd_rh(vpd, rh)
            if t_eff is not None:
                t_scatter = t_eff + t_off + leaf_off
                self._place_point(self.p_ex, t_scatter, rh)
    
                self._mirror["ex"] = {"t": t_scatter, "h": rh, "vpd": vpd}
            else:
                self.p_ex.pos = (-1000, -1000)
        else:
            self.p_ex.pos = (-1000, -1000)
    
        # -------------------------
        # VALUE BOX (NUR TILES!)
        # -------------------------
        self._unit_t = tile_t_in.unit if tile_t_in else ""
        self._unit_h = tile_h_in.unit if tile_h_in else ""
    
        self._box = {
            "in": {
                "t": self._last_float(tile_t_in.buffers.get(f"{prefix}_temp_in")) if tile_t_in else None,
                "h": self._last_float(tile_h_in.buffers.get(f"{prefix}_hum_in")) if tile_h_in else None,
                "vpd": self._last_float(vpd_in),
            },
            "ex": {
                "t": self._last_float(tile_t_ex.buffers.get(f"{prefix}_temp_ex")) if tile_t_ex else None,
                "h": self._last_float(tile_h_ex.buffers.get(f"{prefix}_hum_ex")) if tile_h_ex else None,
                "vpd": self._last_float(vpd_ex),
            },
        }
    
        self._update_value_box()
    # -------------------------------------------------
    def _place_point(self, ellipse, temp, hum):
        gx, gy = self.graph.pos
        gw, gh = self.graph.size
    
        xr = max(self.graph.xmax - self.graph.xmin, 0.0001)
        yr = max(self.graph.ymax - self.graph.ymin, 0.0001)
    
        # clamp
        hum = min(max(hum, self.graph.xmin), self.graph.xmax)
        temp = min(max(temp, self.graph.ymin), self.graph.ymax)
    
        # X = Humidity → rechts
        x = gx + (hum - self.graph.xmin) / xr * gw
    
        # Y = Temperatur → oben heiß, unten kalt (invertiert)
        y = gy + (1.0 - (temp - self.graph.ymin) / yr) * gh
    
        ellipse.pos = (
            x - ellipse.size[0] / 2,
            y - ellipse.size[1] / 2
        )
    # -------------------------------------------------
    # GSM UPDATE
    # -------------------------------------------------
    def update_from_global(self, d):
        self.header.update_from_global(d)
        self.header.set_clock(time.strftime("%H:%M:%S"))
        self._load_points()

    def _tick(self, *_):
        pass
    def _update_value_box(self):
        def fmt(v, unit=""):
            return "--" if v is None else f"{v:.2f}{unit}"
    
        ut = getattr(self, "_unit_t", "")
        uh = getattr(self, "_unit_h", "")
    
        b = getattr(self, "_box", None)
        if not b:
            return
    
        self.value_label.text = (
            "[font=FA][color=#FFD933]\uf111[/color][/font] [b]IN[/b]\n"


            f"  T: {fmt(b['in']['t'], ut)}   "
            f"H: {fmt(b['in']['h'], uh)}\n"
            f"  VPD: {fmt(b['in']['vpd'], ' kPa')}\n\n"
        
            "[font=FA][color=#4DFF4D]\uf111[/color][/font] [b]EX[/b]\n"

            f"  T: {fmt(b['ex']['t'], ut)}   "
            f"H: {fmt(b['ex']['h'], uh)}\n"
            f"  VPD: {fmt(b['ex']['vpd'], ' kPa')}\n\n"
        
            "[color=#AAAAAA][i]Leaf Offset:[/i][/color] "
            f"{fmt(getattr(self, '_leaf_offset', None), '°C')}"

        )
    # ============================================================
    # DEVICE SWIPE (HORIZONTAL)
    # ============================================================
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._touch_start_x = touch.x
            self._touch_active = True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if not self._touch_active or self._touch_start_x is None:
            return super().on_touch_move(touch)

        dx = touch.x - self._touch_start_x

        if abs(dx) >= self._swipe_threshold:
            touch.grab(self)

            if dx < 0:
                self._next_device()
            else:
                self._prev_device()

            self._touch_active = False
            self._touch_start_x = None
            touch.ungrab(self)
            return True

        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            return True

        self._touch_active = False
        self._touch_start_x = None
        return super().on_touch_up(touch)

    def _next_device(self):
        lst = self.gsm.get_device_list()
        if not lst:
            return
        self.gsm.set_active_index((self.gsm.active_index + 1) % len(lst))

    def _prev_device(self):
        lst = self.gsm.get_device_list()
        if not lst:
            return
        self.gsm.set_active_index((self.gsm.active_index - 1) % len(lst))

    # -------------------------------------------------
    # RESET
    # -------------------------------------------------
    def reset_from_global(self):
        self.p_in.pos = (-1000, -1000)
        self.p_ex.pos = (-1000, -1000)
    
        self._mirror = {
            "in": {"t": None, "h": None, "vpd": None},
            "ex": {"t": None, "h": None, "vpd": None},
        }
    
        self._update_value_box()