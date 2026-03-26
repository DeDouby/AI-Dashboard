import threading
import requests
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.clock import Clock

from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled

class ExhaustFanOverlay(FloatLayout):
    def __init__(self, parent_header, **kwargs):
        super().__init__(**kwargs)
        self.parent_header = parent_header
        self._pending_updates = {} 
        self._last_payload = {}    
        self._user_active = False 
        
        # Taktgeber für Sync und UI-Refresh
        self._sync_event = Clock.schedule_interval(self._sync_to_device, 1.3)
        self._update_event = Clock.schedule_interval(self.update_ui, 1.5)

        # 1. HINTERGRUND
        bg = Button(background_color=(0, 0, 0, 0.25))
        bg.bind(on_release=lambda *_: self.close())
        self.add_widget(bg)

        # 2. PANEL
        self.panel = BoxLayout(
            orientation="vertical",
            padding=dp_scaled(20),
            spacing=dp_scaled(10),
            size_hint=(None, None),
            size=(dp_scaled(340), dp_scaled(450)),
            pos_hint={"right": 0.98, "top": 0.98}
        )

        with self.panel.canvas.before:
            Color(0, 0, 0, 0.65)
            self.bg_rect = RoundedRectangle(radius=[dp_scaled(20)])
            # Akzentfarbe: Blau für Exhaust
            Color(0, 0.7, 1, 0.4)
            self.outline = Line(width=1.2)

        self.panel.bind(pos=self._update_canvas, size=self._update_canvas)

        # --- UI CONTENT ---
        self.panel.add_widget(Label(
            text="EXHAUST FAN CONTROL", font_size=sp_scaled(18),
            bold=True, color=(0, 0.7, 1, 1), size_hint_y=None, height=dp_scaled(30)
        ))

        # Große Prozentanzeige
        self.lbl_val = Label(text="0% - 0%", font_size=sp_scaled(38), bold=True, size_hint_y=None, height=dp_scaled(60))
        self.panel.add_widget(self.lbl_val)

        # RPM Label
        self.lbl_rpm = Label(text="RPM: 0", font_size=sp_scaled(20), color=(0.7, 0.7, 1, 1), size_hint_y=None, height=dp_scaled(30))
        self.panel.add_widget(self.lbl_rpm)

        # --- SLIDER SEKTION ---
        self.panel.add_widget(Label(text="MAX EXHAUST SPEED", font_size=sp_scaled(12), color=(0, 0.7, 1, 0.5), size_hint_y=None, height=dp_scaled(15)))
        self.slider_max = Slider(min=0, max=100, value=60, step=1, size_hint_y=None, height=dp_scaled(35))
        self.slider_max.bind(value=self._on_slider_change, on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.slider_max)
        
        self.panel.add_widget(Label(text="MIN EXHAUST SPEED", font_size=sp_scaled(12), color=(0, 0.7, 1, 0.5), size_hint_y=None, height=dp_scaled(15)))
        self.slider_min = Slider(min=0, max=100, value=20, step=1, size_hint_y=None, height=dp_scaled(35))
        self.slider_min.bind(value=self._on_slider_change, on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.slider_min)

        # --- BUTTONS ---
        btn_row = BoxLayout(size_hint_y=None, height=dp_scaled(50), spacing=dp_scaled(10))
        self.btn_man = self._create_styled_btn("MANUAL")
        self.btn_auto = self._create_styled_btn("AUTO")
        self.btn_boost = self._create_styled_btn("BOOST")

        self.btn_man.bind(on_release=lambda *_: self._set_mode("man"))
        self.btn_auto.bind(on_release=lambda *_: self._set_mode("auto"))
        self.btn_boost.bind(on_release=lambda *_: self._set_mode("boost"))

        btn_row.add_widget(self.btn_man); btn_row.add_widget(self.btn_auto); btn_row.add_widget(self.btn_boost)
        self.panel.add_widget(btn_row)

        # FERTIG Button
        btn_close = Button(text="FERTIG", size_hint_y=None, height=dp_scaled(45), background_normal="", background_color=(0.2, 0.2, 0.2, 1), color=(1, 1, 1, 1), bold=True)
        btn_close.bind(on_release=lambda *_: self.close())
        self.panel.add_widget(btn_close)

        self.add_widget(self.panel)

    def _create_styled_btn(self, text):
        return Button(text=text, background_normal="", background_color=(0.2, 0.2, 0.2, 1), color=(1, 1, 1, 1), bold=True, font_size=sp_scaled(12))

    def _on_slider_change(self, instance, value):
        if self.slider_min.value > self.slider_max.value:
            if instance == self.slider_min: self.slider_max.value = value
            else: self.slider_min.value = value
        self.lbl_val.text = f"{int(self.slider_min.value)}% - {int(self.slider_max.value)}%"
        self._pending_updates["ex_fan_pct"] = int(self.slider_max.value)
        self._pending_updates["ex_fan_min"] = int(self.slider_min.value)

    def update_ui(self, *_):
        if self._user_active: return 
        try:
            ip = GLOBAL_STATE.get_active_device_ip()
            if not ip: return
            r = requests.get(f"http://{ip}/data", timeout=0.8)
            if r.status_code == 200:
                j = r.json()
                rpm = j.get("ex_rpm", -256) # Dummy Pseudo-Wert laut deiner Vorgabe
                f_min = j.get("ex_fan_min", 0)
                f_max = j.get("ex_fan_pct", 0)
                mode = j.get("ex_mode", "man")
                
                self.lbl_rpm.text = f"RPM: {rpm}"
                if not self._pending_updates:
                    self.slider_min.value = f_min
                    self.slider_max.value = f_max
                    self.lbl_val.text = f"{int(f_min)}% - {int(f_max)}%"
                    # Blaues Highlight für aktiven Mode
                    active_clr = (0, 0.7, 1, 0.6)
                    inactive_clr = (0.2, 0.2, 0.2, 1)
                    self.btn_man.background_color = active_clr if mode == "man" else inactive_clr
                    self.btn_auto.background_color = active_clr if mode == "auto" else inactive_clr
                    self.btn_boost.background_color = active_clr if mode == "boost" else inactive_clr
        except: pass

    def _sync_to_device(self, dt):
        if not self._pending_updates or self._pending_updates == self._last_payload: return
        payload = self._pending_updates.copy()
        self._last_payload = payload.copy()
        threading.Thread(target=self._send_json_request, args=(payload,), daemon=True).start()

    def _send_json_request(self, payload):
        try:
            ip = GLOBAL_STATE.get_active_device_ip()
            if not ip: return
            r = requests.post(f"http://{ip}/control", json=payload, timeout=2.0)
            if r.status_code == 200: self._pending_updates.clear()
        except: pass

    def _set_mode(self, mode):
        self._pending_updates["ex_mode"] = mode

    def _touch_down(self, slider, touch):
        if slider.collide_point(*touch.pos): self._user_active = True

    def _touch_up(self, slider, touch):
        if slider.collide_point(*touch.pos): self._user_active = False

    def _update_canvas(self, obj, *_):
        self.bg_rect.pos = obj.pos
        self.bg_rect.size = obj.size
        self.outline.rounded_rectangle = (obj.x, obj.y, obj.width, obj.height, dp_scaled(20))

    def close(self):
        if self._update_event: self._update_event.cancel()
        if self._sync_event: self._sync_event.cancel()
        if self.parent: self.parent.remove_widget(self)
        GLOBAL_STATE.ui_handler.active_exhaust_overlay = None