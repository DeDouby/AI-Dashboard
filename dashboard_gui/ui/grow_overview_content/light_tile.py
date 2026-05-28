import os
import time
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.app import App
from kivy.graphics import Color, RoundedRectangle, Line

from dashboard_gui.ui.scaling_utils import sp_scaled, dp_scaled
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.overlays.light_overlay import LightOverlay
from dashboard_gui.overlays.base_overlay import BaseOverlayEngine

ASSET_ROOT = os.path.join("dashboard_gui", "assets")
LIGHT_PIC = os.path.join(ASSET_ROOT, "hardware_pics", "electrogrow.png")


class LightTile(BoxLayout):

    def __init__(self, **kw):
        super().__init__(
            orientation="vertical",
            size_hint=(1, 1),
            **kw
        )
        self.val_box_w = dp_scaled(200)
        self.val_box_h = dp_scaled(140)

        self.padding = dp_scaled(10)
        self.spacing = dp_scaled(6)
        self.title_label = Label(
            text="ElectroGrow 720W",
            font_size=sp_scaled(18),
            bold=True,
            halign="left",
            valign="middle",
            size_hint=(1, None),
            height=dp_scaled(35),
            color=(1, 1, 1, 1)
        )
        self.title_label.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))

        self._user_active = False
        self._last_user_action = 0
        self._last_sent_rev = 0
        self._ui_lock = False
        self.engine = BaseOverlayEngine()

        # Main Container
        self.content_container = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=max(dp_scaled(100), self.val_box_h),
            spacing=dp_scaled(2)
        )

        # Image
        self.light_image = Image(
            source=LIGHT_PIC,
            size_hint=(1, None),
            height=dp_scaled(120),
            allow_stretch=True,
            keep_ratio=True
        )
        self.content_container.add_widget(self.light_image)

        # Value Box
        self.value_box = BoxLayout(
            orientation="vertical",
            size_hint=(1, None), # <--- ÄNDERE ZU 1 (statt None)
            # Entferne width=VALUE_BOX_WIDTH komplett!
            height=dp_scaled(150),
            padding=[dp_scaled(10), dp_scaled(5)],
            spacing=dp_scaled(2)
        )

        with self.value_box.canvas.before:
            Color(0, 0, 0, 0.62)
            self.value_bg = RoundedRectangle(radius=[dp_scaled(14)])
            Color(0.1, 0.45, 0.9, 0.35)
            self.value_glow = Line(width=5)
            Color(0.1, 0.45, 0.9, 0.85)
            self.value_border = Line(width=1.3)

        self.value_box.bind(pos=self._update_value_box_canvas, size=self._update_value_box_canvas)

        # Labels
        self.lbl_current = Label(text="LIVE: --%", font_size=sp_scaled(18), bold=True,
                                 halign="left", valign="middle", color=(1, 1, 1, 1))
        self.lbl_target = Label(text="TARGET: --%", font_size=sp_scaled(18),
                                halign="left", valign="middle")
        self.lbl_remaining = Label(text="REST: --:--", font_size=sp_scaled(18),
                                   halign="left", valign="middle")
        self.lbl_status = Label(text="STATUS: INIT", font_size=sp_scaled(18),
                                halign="left", valign="middle", markup=True)
        self.lbl_phase = Label(text="PHASE: --", font_size=sp_scaled(18),
                               halign="left", valign="middle", color=(1, 1, 1, 1))

        self.lbl_phase.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))

        self.value_box.add_widget(self.title_label)
        self.value_box.add_widget(self.lbl_phase)
        for lbl in (self.lbl_current, self.lbl_target, self.lbl_remaining, self.lbl_status):
            lbl.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))
            self.value_box.add_widget(lbl)

        self.content_container.add_widget(self.value_box)
        self.add_widget(self.content_container)

    def _update_value_box_canvas(self, obj, *args):
        x, y = obj.pos
        w, h = obj.size
        r = dp_scaled(14)
        self.value_bg.pos = (x, y)
        self.value_bg.size = (w, h)
        rect = (x, y, w, h, r)
        self.value_glow.rounded_rectangle = rect
        self.value_border.rounded_rectangle = rect

    # ==================== UPDATE ====================
    def update_values(self, data):          # ← wie beim ExhaustTile: "data"
        if not data:
            return

        target = int(data.get('light_target', 0))
        current_hw = int(data.get('light_pct', 0))
        mode = data.get('light_mode', 'man')

        self.lbl_current.text = f"LIVE: {current_hw}%"
        self.lbl_target.text = f"TARGET: {target}%"
        self.lbl_remaining.text = self._calculate_remaining_time(data)

        self._update_phase(data)        # ← plant_phase wird hier verwendet
        # Status
        server_init = int(data.get('rev_init_light', 0))
        server_rev = int(data.get('rev_light', 0))

        if self.engine.adopt_new_session(server_init, server_rev):
            self._last_sent_rev = server_rev
            return

        status = self.engine.get_status(
            server_init, server_rev, self._user_active, self._last_user_action
        )

        if status == "green":
            if mode == "man":
                self.lbl_status.text = "STATUS: [color=00ff00]MANU[/color]"
            elif mode == "tim":
                self.lbl_status.text = "STATUS: [color=00ff00]TIMER[/color]"
            else:
                self.lbl_status.text = "STATUS: [color=00ff00]OK[/color]"
        elif status in ("retry", "error"):
            self.lbl_status.text = "STATUS: [color=ff4c00]ERR[/color]"
        else:
            self.lbl_status.text = "STATUS: [color=ff8000]PEND[/color]"

    # ==================== PHASE (wie reason beim Exhaust) ====================
    # ==================== PHASE BERECHNUNG (da Server None liefert) ====================
    # ==================== PHASE (mit plant_phase) ====================
    def _update_phase(self, data):
        plant_phase = data.get('plant_phase')
        
        print(f"[DEBUG LightTile] plant_phase = {plant_phase} (Typ: {type(plant_phase)})")

        # Mapping von plant_phase → Anzeige
        if plant_phase == 0:
            self.lbl_phase.text = "PHASE: NIGHT"
            self.lbl_phase.color = (0.45, 0.65, 1.0, 1)
            
        elif plant_phase == 1:
            self.lbl_phase.text = "PHASE: SUNRISE"
            self.lbl_phase.color = (1.0, 0.72, 0.15, 1)
            
        elif plant_phase == 2:
            self.lbl_phase.text = "PHASE: DAY"
            self.lbl_phase.color = (0.0, 1.0, 0.35, 1)
            
        elif plant_phase == 3:
            self.lbl_phase.text = "PHASE: SUNSET"
            self.lbl_phase.color = (1.0, 0.45, 0.1, 1)
            
        else:
            # Fallback
            self.lbl_phase.text = f"PHASE: {plant_phase}"
            self.lbl_phase.color = (1, 1, 1, 1)

    # ==================== TIME ====================
    def _calculate_remaining_time(self, data):
        mode = data.get('light_mode', 'man')
        if mode != "tim":
            return "MANUELL"

        try:
            h = int(data.get('l_start_h', 8))
            m = int(data.get('l_start_m', 0))
            dur = int(data.get('l_dur', 720))

            now = time.localtime()
            current_min = now.tm_hour * 60 + now.tm_min
            start_min = h * 60 + m
            end_min = start_min + dur

            if start_min <= current_min < end_min:
                rem_min = end_min - current_min
                return f"REST: {rem_min // 60}h {rem_min % 60:02d}m"

            wait_min = (start_min - current_min + 1440) % 1440
            return f"IN: {wait_min // 60}h {wait_min % 60:02d}m"
        except Exception:
            return "REST: --:--"

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        ui = GLOBAL_STATE.ui_handler
        if getattr(ui, "active_light_overlay", None):
            ui.active_light_overlay.close()

        overlay = LightOverlay(parent_header=self)
        ui.active_light_overlay = overlay
        App.get_running_app().root.current_screen.add_widget(overlay)
        return True