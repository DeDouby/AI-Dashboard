###############################################################################
# !!! ABSOLUTES GESETZ: DAS TARGET-REVISION-PRINZIP (LIGHT MODULE) !!!
# -----------------------------------------------------------------------------
# JEDE KI, DIE DIESEN CODE BEARBEITET, MUSS DIESE STRUKTUR EINHALTEN. 
# ABWEICHUNGEN FÜHREN ZU SYSTEM-CRASH UND LOGIK-FEHLERN!
###############################################################################

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
        self._update_event = Clock.schedule_interval(self.update_ui, 1.0)
        self._sync_event = Clock.schedule_interval(self._sync_to_client, 1.3)
        self._locked = True
        self._pending_updates = {} 
        self._ui_lock = False # Das hat gefehlt und führt zu Abstürzen/Fehlern
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
        self.lbl_title = Label(text="LIGHT CONTROL PRO", bold=True, color=(0, 1, 0, 1), font_size=sp_scaled(15))
        
        self.sync_icon = Button(text="[font=FA]\uf021[/font]", markup=True, font_size=sp_scaled(30),
                                background_color=(0, 0, 0, 0), color=(1, 1, 1, 1), size_hint_x=None, width=dp_scaled(45))
        self.sync_icon.bind(on_release=self._force_sync)
        title_row.add_widget(self.lbl_title)
        title_row.add_widget(self.sync_icon)
        self.panel.add_widget(title_row)

        # Wert-Box
        val_box = BoxLayout(size_hint_y=None, height=dp_scaled(35))
        self.lbl_val = Label(text="0%", font_size=sp_scaled(42), bold=True, size_hint_x=None, width=dp_scaled(140))
        self.lbl_status_text = Label(text="STATUS: INIT", font_size=sp_scaled(15), bold=True, color=(0, 1, 0, 0.7))
        val_box.add_widget(self.lbl_val)
        val_box.add_widget(self.lbl_status_text)
        self.panel.add_widget(val_box)

        # Main Brightness
        self.slider = UnifiedSlider(min=0, max=100, mode='single', size_hint_y=None, height=dp_scaled(38))
        self.slider.bind(value=self._on_slider_change, on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.slider)

        # Sunrise/Sunset
        self.lbl_sunrise_sunset = Label(text="RAMPEN: --", markup=True, font_size=sp_scaled(15), color=(1, 0.8, 0.2, 0.8), size_hint_y=None, height=dp_scaled(15))
        self.panel.add_widget(self.lbl_sunrise_sunset)
        self.slider_sunrise_sunset = UnifiedSlider(
            min=1,
            max=96,
            mode='range',
            fill_entire_track=True
        )        
        
        self.slider_sunrise_sunset.bind(min_value=self._on_sunrise_sunset_change, max_value=self._on_sunrise_sunset_change, on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.slider_sunrise_sunset)

        # Startzeit
        self.lbl_start = Label(text="START: --", font_size=sp_scaled(15), size_hint_y=None, height=dp_scaled(15))
        self.panel.add_widget(self.lbl_start)
        self.slider_start = UnifiedSlider(min=0, max=95, mode='single', size_hint_y=None, height=dp_scaled(38))
        self.slider_start.bind(value=self._on_start_change, on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.slider_start)

        # Dauer
        self.lbl_dur = Label(text="DAUER: --", font_size=sp_scaled(15), size_hint_y=None, height=dp_scaled(15))
        self.panel.add_widget(self.lbl_dur)
        self.slider_dur = UnifiedSlider(min=1, max=96, mode='single', size_hint_y=None, height=dp_scaled(38))
        self.slider_dur.bind(value=self._on_dur_change, on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.slider_dur)

        self.panel.add_widget(Widget())

        self.lbl_remaining = Label(text="RESTZEIT: --", font_size=sp_scaled(15), color=(1, 0.8, 0, 1), size_hint_y=None, height=dp_scaled(20))
        self.panel.add_widget(self.lbl_remaining)

        # Buttons
        btn_row = BoxLayout(size_hint_y=None, height=dp_scaled(40), spacing=dp_scaled(8))
        self.btn_man = self._create_styled_btn("MANUELL")
        self.btn_tim = self._create_styled_btn("TIMER")
        self.btn_off = self._create_styled_btn("AUS")
        btn_row.add_widget(self.btn_man); btn_row.add_widget(self.btn_tim); btn_row.add_widget(self.btn_off)
        self.panel.add_widget(btn_row)

        self.btn_man.bind(on_release=lambda *_: self._set_mode("man"))
        self.btn_tim.bind(on_release=lambda *_: self._set_mode("tim"))
        self.btn_off.bind(on_release=lambda *_: self._set_mode("off"))

        # Lock & Logic
        self.lock_overlay = LockOverlay(parent=self, panel=self.panel, unlock_callback=self._on_unlock)
        Clock.schedule_once(lambda dt: self.lock_overlay.create(), 0.3)
        self._update_event = Clock.schedule_interval(self.update_ui, 1.0)
        Clock.schedule_once(self._init_values, 0.1)
        self.add_widget(self.panel)

    def _create_styled_btn(self, text):
        return Button(text=text, markup=True, background_normal="", background_color=(0.15, 0.15, 0.15, 1), 
                      color=(0.5, 0.5, 0.5, 1), font_size=sp_scaled(15))

    # ========================================================
    # ZENTRALE LOGIK: TARGET-REVISION & rev_init
    # ========================================================
    def update_ui(self, *_):
        mac = GLOBAL_STATE.get_active_device_id()
        server_data = GLOBAL_STATE.overlay_engine.get_latest_device_data(mac)
        if not server_data: return
    
        # 1. SESSION CHECK
        current_init_rev = int(server_data.get('rev_init_light', 0))
        if not hasattr(self, "_last_adopted_init") or self._last_adopted_init != current_init_rev:
            self._last_adopted_init = current_init_rev
            self._ui_lock = True
            self._apply_server_snapshot(server_data)
            self._ui_lock = False
            return
    
        # 2. REVISION LOGIK
        server_rev = int(server_data.get('rev_light', 0))
        last_sent = getattr(self, '_last_sent_rev', 0)
        
        time_since_action = time.time() - self._last_user_action
        # Synced nur wenn Revisionen passen UND User fertig ist (1.5s Pause)
        is_synced = (server_rev >= last_sent) and not self._user_active and (time_since_action > 1.5)
    
        # LIVE FEEDBACK (Immer aktuell anzeigen)
        eff_pct = server_data.get('light_pct', 0)
        target_pct = server_data.get('light_target', 0)
        self.lbl_val.text = f"{int(eff_pct)}%"
        # Gelbe Farbe wenn Lampe gerade dimmt (Ramp läuft)
        self.lbl_val.color = (1, 0.8, 0, 1) if abs(eff_pct - target_pct) > 0.5 else (1, 1, 1, 1)
    
        if not is_synced:
            # STATUS ORANGE: Wir zeigen stur unser lokales Target
            self.sync_icon.text = "[font=FA]\uf021[/font]"
            self.sync_icon.color = (1, 0.5, 0, 1)
            return

        # === STATUS GRÜN (SYNCED) ===
        self.sync_icon.text = "[font=FA]\uf058[/font]"
        self.sync_icon.color = (0, 1, 0, 1)
    
        if not self._user_active:
            self._ui_lock = True
            self._apply_server_snapshot(server_data)
            self._ui_lock = False
            
    def _apply_server_snapshot(self, data):
        """Hardware -> UI ohne Feedback-Loop"""
        mode = data.get('light_mode', 'man')
        target = data.get('light_target', 0)
        h, m = data.get('l_start_h', 8), data.get('l_start_m', 0)
        dur = data.get('l_dur', 720)
        srise, sset = data.get('l_sunrise', 60), data.get('l_sunset', 60)

        # Slider nur setzen wenn Differenz groß genug (Jitter-Schutz)
        if abs(self.slider.value - target) > 0.5:
            self.slider.value = target
            
        start_val = (h * 60 + m) // 15
        if self.slider_start.value != start_val:
            self.slider_start.value = start_val
            
        dur_steps = dur // 15
        if self.slider_dur.value != dur_steps:
            self.slider_dur.value = dur_steps

        # Sunrise/Sunset Logik
        self.slider_sunrise_sunset.range_max = dur_steps
        new_min = srise // 15
        new_max = dur_steps - (sset // 15)
        
        if abs(self.slider_sunrise_sunset.min_value - new_min) > 0.1:
            self.slider_sunrise_sunset.min_value = new_min
        if abs(self.slider_sunrise_sunset.max_value - new_max) > 0.1:
            self.slider_sunrise_sunset.max_value = new_max

        # Labels aktualisieren
        self.lbl_start.text = f"START: {h:02d}:{m:02d}"
        self.lbl_dur.text = f"DAUER: {dur//60}h {dur%60:02d}m"
        self._update_ramp_label(srise, sset)
        self._apply_button_styles(mode, target)
        
        # Restzeit
        rem = data.get('light_remaining', -1)
        if mode == "tim":
            self.lbl_status_text.text = "TIMER: AKTIV" if target > 0 else "TIMER: SCHLAF"
            self.lbl_remaining.text = f"NÄCHSTER SWITCH: {rem//60}h {rem%60:02d}m" if rem >= 0 else "--"
        else:
            self.lbl_status_text.text = "MODUS: MANUELL"
            self.lbl_remaining.text = "Timer deaktiviert"

        self._target_mode = mode

    def _sync_to_client(self, dt):
        if not self._pending_updates: return
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac: return
        try:
            data = {}
            if os.path.exists(self.sync_path):
                with open(self.sync_path, "r") as f:
                    content = f.read()
                    if content: data = json.loads(content)
            if mac not in data: data[mac] = {}
            data[mac].update(self._pending_updates)
            tmp_path = self.sync_path + ".tmp"
            with open(tmp_path, "w") as f: json.dump(data, f)
            os.replace(tmp_path, self.sync_path)
            self._pending_updates.clear()
        except: pass

    def _send_command(self, **kwargs):
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac or not self._init_done: return
        
        start_min = int(self.slider_start.value) * 15
        sr_min = int(self.slider_sunrise_sunset.min_value) * 15
        ss_min = int(self.slider_sunrise_sunset.range_max - self.slider_sunrise_sunset.max_value) * 15

        rev = GLOBAL_STATE.send_overlay_command(
            "light",
            pct=int(self.slider.value),
            mode=kwargs.get("mode", self._target_mode),
            h=start_min // 60, m=start_min % 60,
            dur=int(self.slider_dur.value) * 15,
            sunrise=sr_min, sunset=ss_min
        )
        if rev:
            self._last_sent_rev = rev
            self.sync_icon.color = (1, 0.5, 0, 1)

    def _on_slider_change(self, *args):
        if not self._init_done or self._ui_lock: 
            return
        if not self._init_done or self._locked: return
        self.lbl_val.text = f"{int(self.slider.value)}%"
        self.sync_icon.color = (1, 0.5, 0, 1)

    def _on_dur_change(self, instance, value):
        if not self._init_done or self._ui_lock: 
            return
        if not self._init_done: return
        steps = int(value)
        self.lbl_dur.text = f"DAUER: {(steps*15)//60}h {(steps*15)%60:02d}m"
        self.slider_sunrise_sunset.range_max = steps # Range-Slider anpassen

    def _on_start_change(self, instance, value):
        if not self._init_done or self._ui_lock: 
            return
        if not self._init_done: return
        m = int(value) * 15
        self.lbl_start.text = f"START: {m//60:02d}:{m%60:02d}"

    def _update_ramp_label(self, sr, ss):
        self.lbl_sunrise_sunset.text = f"[font=FA]\uf185[/font] SUNRISE: {sr}m | [font=FA]\uf186[/font] SUNSET: {ss}m"

    def _on_sunrise_sunset_change(self, *args):
        if not self._init_done or self._ui_lock: 
            return
        if not self._init_done: return
        sr = int(self.slider_sunrise_sunset.min_value) * 15
        ss = int(self.slider_sunrise_sunset.range_max - self.slider_sunrise_sunset.max_value) * 15
        self._update_ramp_label(sr, ss)

    def _touch_down(self, slider, touch):
        if not self._locked and slider.collide_point(*touch.pos): self._user_active = True

    def _touch_up(self, slider, touch):
        if self._user_active:
            self._user_active = False
            self._last_user_action = time.time()
            self._send_command()

    def _set_mode(self, mode):
        if not self._locked: self._send_command(mode=mode)

    def _on_unlock(self):
        self._locked = False
        for s in [self.slider, self.slider_start, self.slider_dur, self.slider_sunrise_sunset]: s.disabled = False

    def _force_sync(self, *_): self._send_command()

    def _init_values(self, *_):
        mac = GLOBAL_STATE.get_active_device_id()
        data = GLOBAL_STATE.overlay_engine.get_buffer_data(mac)
    
        if not data:
            Clock.schedule_once(self._init_values, 0.3)
            return
    
        # === 1. WERTE HOLEN ===
        mode = data.get('light_mode', 'man')
        target = data.get('light_target', 0)
    
        h = data.get('l_start_h', 8)
        m = data.get('l_start_m', 0)
        dur = data.get('l_dur', 720)
    
        srise = data.get('l_sunrise', 60)
        sset = data.get('l_sunset', 60)
    
        # === 2. UI LOCK (WICHTIG!) ===
        self._ui_lock = True
    
        # --- MAIN SLIDER ---
        self.slider.value = target
    
        # --- START ---
        self.slider_start.value = (h * 60 + m) // 15
    
        # --- DURATION ---
        dur_steps = dur // 15
        self.slider_dur.value = dur_steps
    
        # --- SUNRISE / SUNSET ---
        self.slider_sunrise_sunset.range_max = dur_steps
        self.slider_sunrise_sunset.min_value = srise // 15
        self.slider_sunrise_sunset.max_value = dur_steps - (sset // 15)
    
        # === UNLOCK ===
        self._ui_lock = False
    
        # === 3. LABELS (EXPLIZIT!) ===
        self.lbl_val.text = f"{int(target)}%"
        self.lbl_start.text = f"START: {h:02d}:{m:02d}"
        self.lbl_dur.text = f"DAUER: {dur//60}h {dur%60:02d}m"
        self._update_ramp_label(srise, sset)
    
        # === 4. BUTTONS ===
        self._apply_button_styles(mode)
    
        # === 5. STATE ===
        self._target_mode = mode
        self._last_sent_rev = int(data.get('rev_light', 0))
    
        # === 6. FINALIZE ===
        self._pending_updates.clear()
        self._init_done = True
    
        # Slider freigeben
        self.slider.disabled = False
        self.slider_start.disabled = False
        self.slider_dur.disabled = False
        self.slider_sunrise_sunset.disabled = False

    def _apply_button_styles(self, mode, target=0): # target als optionaler Parameter
        c_bg = (0.15, 0.15, 0.15, 1)
        
        # MANUELL Button
        self.btn_man.background_color = (0, 1, 0, 0.8) if mode == "man" else c_bg
        self.btn_man.color = (1, 1, 1, 1) if mode == "man" else (0.6, 0.6, 0.6, 1)
        
        # TIMER Button
        self.btn_tim.background_color = (0, 0.6, 1, 0.8) if mode == "tim" else c_bg
        self.btn_tim.color = (1, 1, 1, 1) if mode == "tim" else (0.6, 0.6, 0.6, 1)
        
        # AUS Button (Leuchtet rot, wenn Modus manuell UND target 0)
        is_off = (mode == "off") or (mode == "man" and target < 1)
        self.btn_off.background_color = (1, 0.2, 0.2, 0.8) if is_off else c_bg
        self.btn_off.color = (1, 1, 1, 1) if is_off else (0.6, 0.6, 0.6, 1)
    def _u(self, *_):
        self.bg_rect.pos, self.bg_rect.size = self.panel.pos, self.panel.size
        self.outline.rounded_rectangle = (self.panel.x, self.panel.y, self.panel.width, self.panel.height, dp_scaled(20))

    def close(self):
        if self._update_event: self._update_event.cancel()
        if self.parent: self.parent.remove_widget(self)
        GLOBAL_STATE.ui_handler.active_light_overlay = None