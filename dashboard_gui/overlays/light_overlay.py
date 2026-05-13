###############################################################################
# !!! REPARIERTES OVERLAY: RESTZEIT & LOGIK WIEDERHERGESTELLT !!!
###############################################################################

import os
import json
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.clock import Clock
import time 
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.overlays.unified_slider import UnifiedSlider
from dashboard_gui.overlays.lock_overlay import LockOverlay
from dashboard_gui.overlays.base_overlay import BaseOverlayEngine
from kivy.uix.widget import Widget

class LightOverlay(FloatLayout):
    def __init__(self, parent_header, **kwargs):
        super().__init__(**kwargs)
        self.parent_header = parent_header
        self._user_active = False 
        self._last_user_action = 0 
        self._init_done = False
        self._locked = True
        self._target_mode = "tim"
        self._last_sent_rev = 0
        self._last_send_time = 0
        self._retry_count = 0
        self._max_retries = 5
        self._ui_lock = False
        self._pending_updates = {}
        self.sync_path = os.path.join("data", "settings_sync.json")
        self.engine = BaseOverlayEngine()
        # Hintergrund
        bg = Button(background_color=(0, 0, 0, 0.25))
        bg.bind(on_release=lambda *_: self.close())
        self.add_widget(bg)

        # Panel
        self.panel = BoxLayout(
            orientation="vertical", 
            spacing=dp_scaled(7),
            size_hint=(None, None), 
            size=(dp_scaled(440), dp_scaled(480)), 
            padding=[dp_scaled(25), dp_scaled(15), dp_scaled(25), dp_scaled(25)],
            pos_hint={"right": 0.98, "top": 0.98}
        )

        with self.panel.canvas.before:
            Color(0, 0, 0, 0.75)
            self.bg_rect = RoundedRectangle(radius=[dp_scaled(20)])
            Color(0, 1, 0, 0.3)
            self.outline = Line(width=1.2)

        self.panel.bind(pos=self._u, size=self._u)

        # Header
        title_row = BoxLayout(size_hint_y=None, height=dp_scaled(40), spacing=dp_scaled(5))
        self.lbl_title = Label(text="LIGHT CONTROL PRO", bold=True, color=(0, 1, 0, 1), font_size=sp_scaled(18))
        self.sync_icon = Button(text="[font=FA]\uf021[/font]", markup=True, font_size=sp_scaled(30),
                                background_color=(0, 0, 0, 0), color=(1, 1, 1, 1), size_hint_x=None, width=dp_scaled(45))
        self.sync_icon.bind(on_release=self._force_sync)
        title_row.add_widget(self.lbl_title)
        title_row.add_widget(self.sync_icon)
        self.panel.add_widget(title_row)

        # Wert-Box
        val_box = BoxLayout(size_hint_y=None, height=dp_scaled(35))
        self.lbl_val = Label(text="0%", font_size=sp_scaled(36), bold=True, size_hint_x=None, width=dp_scaled(140))
        self.lbl_target = Label(text="(TARGET: 0%)", font_size=sp_scaled(20), color=(0.7, 0.7, 0.7, 0.8), size_hint_x=None, width=dp_scaled(100))
        self.lbl_status_text = Label(text="STATUS: INIT", font_size=sp_scaled(18), bold=True, color=(0, 1, 0, 0.7))
        val_box.add_widget(self.lbl_val); val_box.add_widget(self.lbl_target); val_box.add_widget(self.lbl_status_text)
        self.panel.add_widget(val_box)

        # Main Brightness
        self.slider = UnifiedSlider(min=0, max=100, mode='single', size_hint_y=None, height=dp_scaled(38))
        self.slider.bind(value=self._on_slider_change, on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.slider)

        # Sunrise/Sunset
        self.lbl_sunrise_sunset = Label(text="RAMPEN: --", markup=True, font_size=sp_scaled(18), color=(1, 0.8, 0.2, 0.8), size_hint_y=None, height=dp_scaled(15))
        self.panel.add_widget(self.lbl_sunrise_sunset)
        self.slider_sunrise_sunset = UnifiedSlider(min=1, max=96, mode='range', fill_entire_track=True)        
        self.slider_sunrise_sunset.bind(min_value=self._on_sunrise_sunset_change, max_value=self._on_sunrise_sunset_change, on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.slider_sunrise_sunset)

        # Startzeit
        self.lbl_start = Label(text="START: --", font_size=sp_scaled(18), size_hint_y=None, height=dp_scaled(15))
        self.panel.add_widget(self.lbl_start)
        self.slider_start = UnifiedSlider(min=0, max=95, mode='single', size_hint_y=None, height=dp_scaled(38))
        self.slider_start.bind(value=self._on_start_change, on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.slider_start)

        # Dauer
        self.lbl_dur = Label(text="DAUER: --", font_size=sp_scaled(18), size_hint_y=None, height=dp_scaled(15))
        self.panel.add_widget(self.lbl_dur)
        self.slider_dur = UnifiedSlider(min=1, max=96, mode='single', size_hint_y=None, height=dp_scaled(38))
        self.slider_dur.bind(value=self._on_dur_change, on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.slider_dur)

        self.panel.add_widget(Widget())

        # RESTZEIT LABEL (WIEDER DA!)
        self.lbl_remaining = Label(text="RESTZEIT: --", font_size=sp_scaled(18), color=(1, 0.8, 0, 1), size_hint_y=None, height=dp_scaled(20))
        self.panel.add_widget(self.lbl_remaining)

        # Buttons
        btn_row = BoxLayout(size_hint_y=None, height=dp_scaled(40), spacing=dp_scaled(8))
        self.btn_man = self._create_styled_btn("MANUELL"); self.btn_tim = self._create_styled_btn("TIMER"); self.btn_off = self._create_styled_btn("AUS")
        btn_row.add_widget(self.btn_man); btn_row.add_widget(self.btn_tim); btn_row.add_widget(self.btn_off)
        self.panel.add_widget(btn_row)

        self.btn_man.bind(on_release=lambda *_: self._set_mode("man"))
        self.btn_tim.bind(on_release=lambda *_: self._set_mode("tim"))
        self.btn_off.bind(on_release=lambda *_: self._set_mode("off"))

        self.lock_overlay = LockOverlay(parent=self, panel=self.panel, unlock_callback=self._on_unlock)
        Clock.schedule_once(lambda dt: self.lock_overlay.create(), 0.3)
        Clock.schedule_once(self._init_values, 0.1)
        
        self._update_event = Clock.schedule_interval(self.update_ui, 1.0)
        self.add_widget(self.panel)

    def _create_styled_btn(self, text):
        return Button(text=text, markup=True, background_normal="", background_color=(0.15, 0.15, 0.15, 1), color=(0.5, 0.5, 0.5, 1), font_size=sp_scaled(18))

    def _init_values(self, *_):
        mac = GLOBAL_STATE.get_active_device_id()
        data = GLOBAL_STATE.overlay_engine.get_buffer_data(mac)
        if not data: Clock.schedule_once(self._init_values, 0.3); return
        self._my_handshake_id = self.engine.create_handshake()
        GLOBAL_STATE.overlay_engine.send_light_handshake(mac, self._my_handshake_id)
        self._ui_lock = True
        self._apply_server_snapshot(data)
        self._ui_lock = False
        self._init_done = True

    def _apply_server_snapshot(self, data):
        if not data: return
        mode = data.get('light_mode', 'man')
        target = int(data.get('light_target', 0))    # Dein eingestellter Wert
        current_hw = int(data.get('light_pct', 0))   # Was die Lampe wirklich tut
        
        h, m = int(data.get('l_start_h', 8)), int(data.get('l_start_m', 0))
        dur, srise, sset = int(data.get('l_dur', 720)), int(data.get('l_sunrise', 60)), int(data.get('l_sunset', 60))

        # --- LOGIK: GOLDENE STUNDE ---
        # Wenn im Timer-Modus der Ist-Wert vom Soll-Wert abweicht (Rampe aktiv)
        if mode == "tim" and current_hw != target and current_hw > 0:
            self.lbl_val.color = (1, 0.8, 0, 1) # GOLD-Farbe
        else:
            self.lbl_val.color = (1, 1, 1, 1)    # Standard Weiß

        # Der große Wert repräsentiert deine Einstellung (Target)
        self.lbl_val.text = f"{target}%"
        # Das kleine Label zeigt zur Kontrolle die Hardware-Realität
        self.lbl_target.text = f"({current_hw}%)"

        # --- STATUS TEXT FIX (Weg von INIT) ---
        if mode == "off":
            self.lbl_status_text.text = "STATUS: AUS"
            self.lbl_status_text.color = (1, 0.2, 0.2, 0.8)
        elif mode == "man":
            self.lbl_status_text.text = "STATUS: MANUELL"
            self.lbl_status_text.color = (0, 0.8, 1, 1)
        else:
            self.lbl_status_text.text = "STATUS: TIMER"
            self.lbl_status_text.color = (0, 1, 0, 1)

        # Slider-Werte setzen
        self.slider.value = target
        self.slider_start.value = (h * 60 + m) // 15
        dur_steps = dur // 15
        self.slider_dur.value = dur_steps
        self.slider_sunrise_sunset.range_max = dur_steps
        self.slider_sunrise_sunset.min_value = srise // 15
        self.slider_sunrise_sunset.max_value = dur_steps - (sset // 15)

        self.lbl_start.text = f"START: {h:02d}:{m:02d}"
        self.lbl_dur.text = f"DAUER: {dur//60}h {dur%60:02d}m"
        self._update_ramp_label(srise, sset)
        self._apply_button_styles(mode, target)

    def _calculate_remaining_time(self, data):
        mode = data.get('light_mode', 'man')
        if mode != "tim": 
            return "MODUS: MANUELL/AUS"
        
        h, m = int(data.get('l_start_h', 8)), int(data.get('l_start_m', 0))
        dur = int(data.get('l_dur', 720))  # Dauer in Minuten

        now = time.localtime()
        current_min = now.tm_hour * 60 + now.tm_min
        start_min = h * 60 + m
        end_min = (start_min + dur)  # Kann > 1440 sein

        # 1. Prüfen: Ist das Licht GERADE AN?
        is_active = False
        
        # Fall A: Zeitfenster liegt innerhalb eines Tages (z.B. 08:00 - 20:00)
        if end_min <= 1440:
            if start_min <= current_min < end_min:
                is_active = True
        # Fall B: Zeitfenster geht über Mitternacht (z.B. 20:00 - 04:00)
        else:
            if current_min >= start_min or current_min < (end_min % 1440):
                is_active = True

        # 2. Berechnung der Anzeige
        if is_active:
            # Wie viel Zeit ist noch übrig?
            if current_min >= start_min:
                # Wir sind am ersten Tag des Zyklus
                rem_min = end_min - current_min
            else:
                # Wir sind am zweiten Tag (nach Mitternacht)
                rem_min = (end_min % 1440) - current_min
            
            return f"RESTZEIT: {rem_min // 60}h {rem_min % 60:02d}m"
        else:
            # Licht ist aus -> Berechne Zeit bis zum nächsten Start
            wait_min = (start_min - current_min + 1440) % 1440
            return f"STARTET IN: {wait_min // 60}h {wait_min % 60:02d}m"
        

    def _send_command(self, is_retry=False, **kwargs):
        mac = GLOBAL_STATE.get_active_device_id()
        start_step = max(0, min(95, int(self.slider_start.value)))
        start_min = start_step * 15
        dur_steps = max(1, min(96, int(self.slider_dur.value)))
        dur_min = dur_steps * 15
        if not mac or not self._init_done: return
        start_min = int(self.slider_start.value) * 15
        rev = GLOBAL_STATE.send_overlay_command("light", pct=int(self.slider.value), mode=kwargs.get("mode", self._target_mode),
            h=start_min // 60, m=start_min % 60, dur=int(self.slider_dur.value) * 15,
            sunrise=int(self.slider_sunrise_sunset.min_value) * 15, 
            sunset=int(self.slider_sunrise_sunset.range_max - self.slider_sunrise_sunset.max_value) * 15)
        if rev:
            self.engine.mark_sent(rev)
            self._last_sent_rev = rev   # fallback-safe
            self._last_send_time = time.time()
        
            if not is_retry:
                self.engine.reset_retry()

    def _on_slider_change(self, *args):
        if self._init_done and not self._ui_lock and not self._locked:
            self.lbl_val.text = f"{int(self.slider.value)}%"
            self.sync_icon.color = (1, 0.5, 0, 1)

    def _on_dur_change(self, instance, value):
        if self._init_done and not self._ui_lock:
            steps = max(1, min(96, int(value)))   # 💥 FIX
            self.slider_dur.value = steps         # 💥 wichtig (UI zurückdrücken)
    
            self.lbl_dur.text = f"DAUER: {(steps*15)//60}h {(steps*15)%60:02d}m"
            self.slider_sunrise_sunset.range_max = steps

    def _on_start_change(self, instance, value):
        if self._init_done and not self._ui_lock:
            value = max(0, min(95, int(value)))   # 💥 FIX
            m = value * 15
            self.lbl_start.text = f"START: {m//60:02d}:{m%60:02d}"

    def _update_ramp_label(self, sr, ss):
        self.lbl_sunrise_sunset.text = f"[font=FA]\uf185[/font] SUNRISE: {sr}m | [font=FA]\uf186[/font] SUNSET: {ss}m"

    def _on_sunrise_sunset_change(self, *args):
        if self._init_done and not self._ui_lock:
            sr, ss = int(self.slider_sunrise_sunset.min_value) * 15, int(self.slider_sunrise_sunset.range_max - self.slider_sunrise_sunset.max_value) * 15
            self._update_ramp_label(sr, ss)

    def _touch_down(self, slider, touch):
        if not self._locked and slider.collide_point(*touch.pos): self._user_active = True

    def _touch_up(self, slider, touch):
        if self._user_active:
            self._user_active = False; self._last_user_action = time.time(); self._send_command()

    def _set_mode(self, mode):
        if not self._locked: self._target_mode = mode; self._send_command(mode=mode)

    def _on_unlock(self):
        self._locked = False
        for s in [self.slider, self.slider_start, self.slider_dur, self.slider_sunrise_sunset]: s.disabled = False

    def _force_sync(self, *_): self._send_command()

    def update_ui(self, *_):
        mac = GLOBAL_STATE.get_active_device_id()
        server_data = GLOBAL_STATE.overlay_engine.get_buffer_data(mac)
        if not server_data: return

        # Restzeit-Update bei jedem Tick
        self.lbl_remaining.text = self._calculate_remaining_time(server_data)

        server_init = int(server_data.get('rev_init_light', 0))
        server_rev = int(server_data.get('rev_light', 0))
        is_alive = (server_init == self._my_handshake_id)
        
        if self.engine.adopt_new_session(server_init, server_rev):
            self._last_sent_rev = server_rev
            return
        
        is_alive = self.engine.is_alive(server_init)

        last_sent = getattr(self, '_last_sent_rev', 0)
        pending = self.engine.is_pending(server_rev)
        
        if pending and self.engine.should_retry():
            if self.engine.retry_allowed():
                self.engine.register_retry()
                self._send_command(is_retry=True)
                return
        
        is_synced = self.engine.is_synced(
            server_init,
            server_rev,
            self._user_active,
            self._last_user_action
        )

        is_synced = is_alive and (not pending) and not self._user_active and (time.time() - self._last_user_action > 1.5)
        status = self.engine.get_status(
            server_init,
            server_rev,
            self._user_active,
            self._last_user_action
        )
        
        if status == "green":
            self.sync_icon.text, self.sync_icon.color = "[font=FA]\uf058[/font]", (0, 1, 0, 1)
        elif status == "retry":
            self.sync_icon.text, self.sync_icon.color = "[font=FA]\uf021[/font]", (1, 0.5, 0, 1)
        elif status == "error":
            self.sync_icon.text, self.sync_icon.color = "[font=FA]\uf071[/font]", (1, 0.3, 0, 1)
        else:
            self.sync_icon.text, self.sync_icon.color = "[font=FA]\uf021[/font]", (1, 0.5, 0, 1)
        
        if status != "green":
            return
        if not self._user_active:
            self._ui_lock = True; self._apply_server_snapshot(server_data); self._ui_lock = False

    def _apply_button_styles(self, mode, target=0):
        c_bg = (0.15, 0.15, 0.15, 1)
        self.btn_man.background_color = (0, 1, 0, 0.8) if mode == "man" else c_bg
        self.btn_tim.background_color = (0, 0.6, 1, 0.8) if mode == "tim" else c_bg
        is_off = (mode == "off") or (mode == "man" and int(target) < 1)
        self.btn_off.background_color = (1, 0.2, 0.2, 0.8) if is_off else c_bg

    def _u(self, *_):
        self.bg_rect.pos, self.bg_rect.size = self.panel.pos, self.panel.size
        self.outline.rounded_rectangle = (self.panel.x, self.panel.y, self.panel.width, self.panel.height, dp_scaled(20))
    


    def close(self):
        if self._update_event: self._update_event.cancel()
        if self.parent: self.parent.remove_widget(self)
        GLOBAL_STATE.ui_handler.active_light_overlay = None