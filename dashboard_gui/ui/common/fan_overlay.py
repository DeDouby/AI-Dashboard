from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.clock import Clock
import time 
import json
import os
import config

from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from web_client import WEB_CLIENT 

class FanOverlay(FloatLayout):
    def __init__(self, parent_header, **kwargs):
        super().__init__(**kwargs)
        self.parent_header = parent_header
        self._pending_updates = {} 
        self._user_active = False 
        self._last_user_action = 0 
        
        self.sync_path = os.path.join(config.DATA, "settings_sync.json")

        self._update_event = Clock.schedule_interval(self.update_ui, 1.0)
        self._sync_event = Clock.schedule_interval(self._sync_to_file, 1.3)

        # --- UI SETUP ---
        bg = Button(background_color=(0, 0, 0, 0.25))
        bg.bind(on_release=lambda *_: self.close())
        self.add_widget(bg)

        self.panel = BoxLayout(
            orientation="vertical", padding=dp_scaled(20), spacing=dp_scaled(10),
            size_hint=(None, None), size=(dp_scaled(340), dp_scaled(450)),
            pos_hint={"right": 0.98, "top": 0.98}
        )

        with self.panel.canvas.before:
            Color(0, 0, 0, 0.65)
            self.bg_rect = RoundedRectangle(radius=[dp_scaled(20)])
            Color(0, 1, 0, 0.4)
            self.outline = Line(width=1.2)
        self.panel.bind(pos=self._update_canvas, size=self._update_canvas)

        # --- CONTENT ---
        self.panel.add_widget(Label(text="FAN CONTROL PRO", font_size=sp_scaled(18), bold=True, color=(0, 1, 0, 1)))
        
        self.lbl_val = Label(text="0% - 0%", font_size=sp_scaled(38), bold=True)
        self.panel.add_widget(self.lbl_val)

        self.lbl_rpm = Label(text="RPM: 0", font_size=sp_scaled(20), color=(0.7, 0.7, 1, 1))
        self.panel.add_widget(self.lbl_rpm)

        # MAX SLIDER
        self.panel.add_widget(Label(text="MAX SPEED", font_size=sp_scaled(12), color=(0,1,0,0.5)))
        self.slider_max = Slider(min=0, max=100, step=1, size_hint_y=None, height=dp_scaled(35))
        self.slider_max.bind(value=self._on_slider_change, on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.slider_max)
        
        # MIN SLIDER
        self.panel.add_widget(Label(text="MIN SPEED", font_size=sp_scaled(12), color=(0,1,0,0.5)))
        self.slider_min = Slider(min=0, max=100, step=1, size_hint_y=None, height=dp_scaled(35))
        self.slider_min.bind(value=self._on_slider_change, on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.slider_min)

        # MODES
        btn_row = BoxLayout(size_hint_y=None, height=dp_scaled(50), spacing=dp_scaled(10))
        self.btn_man = self._create_styled_btn("MANUAL")
        self.btn_nat = self._create_styled_btn("NATURAL")
        self.btn_chao = self._create_styled_btn("CHAOTIC")
        self.btn_man.bind(on_release=lambda *_: self._set_mode("man"))
        self.btn_nat.bind(on_release=lambda *_: self._set_mode("nat"))
        self.btn_chao.bind(on_release=lambda *_: self._set_mode("chao"))
        btn_row.add_widget(self.btn_man); btn_row.add_widget(self.btn_nat); btn_row.add_widget(self.btn_chao)
        self.panel.add_widget(btn_row)

        btn_close = Button(text="FERTIG", size_hint_y=None, height=dp_scaled(45), background_color=(0.2, 0.2, 0.2, 1), bold=True)
        btn_close.bind(on_release=lambda *_: self.close())
        self.panel.add_widget(btn_close)
        self.add_widget(self.panel)

    def _create_styled_btn(self, text):
        return Button(text=text, background_normal="", background_color=(0.2, 0.2, 0.2, 1), bold=True, font_size=sp_scaled(12))

    def _on_slider_change(self, instance, value):
        if self.slider_min.value > self.slider_max.value:
            if instance == self.slider_min: self.slider_max.value = value
            else: self.slider_min.value = value
        
        self.lbl_val.text = f"{int(self.slider_min.value)}% - {int(self.slider_max.value)}%"
        
        # DAS HIER IST DER ENTSCHEIDENDE TEIL:
        now = time.time()
        self._pending_updates["fan_pct"] = int(self.slider_max.value)
        self._pending_updates["fan_min"] = int(self.slider_min.value)
        self._pending_updates["_last_change"] = now  # <--- Hier ist der "Macht-Stempel"
        self._last_user_action = now
    def update_ui(self, *_):
        if self._user_active: return 
        
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac: return

        # 1. SOLL-DATEN aus der Datei laden
        saved_min, saved_max, saved_mode, last_change = 0, 0, "man", 0
        if os.path.exists(self.sync_path):
            try:
                with open(self.sync_path, "r") as f:
                    data = json.load(f).get(mac, {})
                    saved_min = data.get("fan_min", 0)
                    saved_max = data.get("fan_pct", 0)
                    saved_mode = data.get("mode", "man")
                    last_change = data.get("_last_change", 0)
            except: pass

        # 2. Prüfen ob wir im "Macht-Fenster" sind (User hat gerade geschoben)
        is_fresh = (time.time() - last_change) < 8.0

        if not self._pending_updates:
            # Wenn wir NICHT gerade selbst schieben, Slider auf gespeicherten Wert
            self.slider_min.value = saved_min
            self.slider_max.value = saved_max
            self.lbl_val.text = f"{int(saved_min)}% - {int(saved_max)}%"
            
            # Button Farben
            self.btn_man.background_color = (0, 1, 0, 0.6) if saved_mode == "man" else (0.2, 0.2, 0.2, 1)
            self.btn_nat.background_color = (0, 1, 0, 0.6) if saved_mode == "nat" else (0.2, 0.2, 0.2, 1)
            self.btn_chao.background_color = (0, 1, 0, 0.6) if saved_mode == "chao" else (0.2, 0.2, 0.2, 1)

        # RPM immer aktuell anzeigen
        server_data = WEB_CLIENT.current_data.get(mac)
        self.lbl_rpm.text = f"RPM: {server_data.get('rpm', 0)}" if server_data else "OFFLINE"
    def _sync_to_file(self, dt):
        """Schreibt Änderungen atomar in die settings_sync.json"""
        if not self._pending_updates: return
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac: return

        data = {}
        if os.path.exists(self.sync_path):
            try:
                with open(self.sync_path, "r") as f:
                    content = f.read()
                    if content: data = json.loads(content)
            except: pass

        if mac not in data: data[mac] = {}
        data[mac].update(self._pending_updates)

        try:
            tmp_path = self.sync_path + ".tmp"
            with open(tmp_path, "w") as f:
                json.dump(data, f)
            os.replace(tmp_path, self.sync_path)
        except Exception as e:
            print(f"Fan-Write Error: {e}")
            
        self._pending_updates.clear()

    def _set_mode(self, mode):
        self._pending_updates["mode"] = mode
        self._pending_updates["_last_change"] = time.time() # <--- Auch hier Stempel setzen!
        self._sync_to_file(0)
    def _touch_down(self, slider, touch):
        if slider.collide_point(*touch.pos): self._user_active = True

    def _touch_up(self, slider, touch):
        if slider.collide_point(*touch.pos): 
            self._user_active = False
            self._last_user_action = time.time()

    def _update_canvas(self, obj, *_):
        self.bg_rect.pos = obj.pos
        self.bg_rect.size = obj.size
        self.outline.rounded_rectangle = (obj.x, obj.y, obj.width, obj.height, dp_scaled(20))

    def close(self):
        if self._update_event: self._update_event.cancel()
        if self._sync_event: self._sync_event.cancel()
        if self.parent: self.parent.remove_widget(self)
        GLOBAL_STATE.ui_handler.active_fan_overlay = None