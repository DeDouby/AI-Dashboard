###############################################################################
# !!! ABSOLUTES GESETZ: DAS TARGET-REVISION-PRINZIP !!!
# -----------------------------------------------------------------------------
# 1. KEINE DIREKTEN SCHALTVORGÄNGE...
###############################################################################

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.clock import Clock
import config 
import time 
import json 
import os
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.overlays.unified_slider import UnifiedSlider
from dashboard_gui.overlays.lock_overlay import LockOverlay
from kivy.uix.widget import Widget


class ExhaustFanOverlay(FloatLayout):
    def __init__(self, parent_header, **kwargs):
        super().__init__(**kwargs)
        self.parent_header = parent_header
        self._user_active = False 
        self._last_user_action = 0 
        self._init_done = False
        self._locked = True
        self._target_mode = "auto"

        # === AUTO-RETRY VARIABLEN ===
        self._last_sent_rev = 0
        self._last_send_time = 0
        self._retry_count = 0
        self._max_retries = 5

        self._ui_lock = False
        self.sync_path = os.path.join(config.DATA, "settings_sync.json")
        self._pending_updates = {}

        # Hintergrund
        bg = Button(background_color=(0, 0, 0, 0.25))
        bg.bind(on_release=lambda *_: self.close())
        self.add_widget(bg)

        # Panel
        self.panel = BoxLayout(
            orientation="vertical", 
            spacing=dp_scaled(8),
            size_hint=(None, None), 
            size=(dp_scaled(420), dp_scaled(480)),
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
        title_row = BoxLayout(size_hint_y=None, height=dp_scaled(35), spacing=dp_scaled(5))
        self.lbl_title = Label(text="EXHAUST FAN CONTROL", bold=True, color=(0, 1, 0, 1),
                               font_size=sp_scaled(15), halign="left", valign="middle")
        self.lbl_title.bind(size=self.lbl_title.setter('text_size'))
        
        self.sync_icon = Button(text="[font=FA]\uf021[/font]", markup=True,
                                font_size=sp_scaled(30), size_hint=(None, None), 
                                width=dp_scaled(45), height=dp_scaled(45),
                                background_color=(0, 0, 0, 0), color=(1, 1, 1, 1))
        self.sync_icon.bind(on_release=self._force_sync)
        
        title_row.add_widget(self.lbl_title)
        title_row.add_widget(self.sync_icon)
        self.panel.add_widget(title_row)

        # Wert-Anzeigen
        self.lbl_val = Label(text="0% - 0%", font_size=sp_scaled(30), bold=True, 
                             size_hint_y=None, height=dp_scaled(30))
        self.panel.add_widget(self.lbl_val)

        info_row = BoxLayout(size_hint_y=None, height=dp_scaled(30))
        self.lbl_rpm = Label(text="RPM: 0", font_size=sp_scaled(14), color=(0.7, 0.7, 1, 0.8))
        self.lbl_live_speed = Label(text="LIVE: 0%", font_size=sp_scaled(14), bold=True, color=(0, 1, 1, 0.8))
        info_row.add_widget(self.lbl_rpm)
        info_row.add_widget(self.lbl_live_speed)
        self.panel.add_widget(info_row)

        # Sliders
        self._add_slider_label("FAN SPEED RANGE")
        self.range_slider = UnifiedSlider(min=0, max=100, mode='range', size_hint_y=None, height=dp_scaled(35))
        self.range_slider.bind(min_value=self._on_slider_change, max_value=self._on_slider_change,
                               on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.range_slider)

        self.lbl_temp = self._add_slider_label("TEMP TARGET", "22° - 28°")
        self.temp_slider = UnifiedSlider(range_min=15, range_max=35, min=22, max=28, mode='range', 
                                       size_hint_y=None, height=dp_scaled(35))
        self.temp_slider.bind(min_value=self._on_env_slider_change, max_value=self._on_env_slider_change,
                              on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.temp_slider)

        self.lbl_hum = self._add_slider_label("HUMIDITY TARGET", "40% - 70%")
        self.hum_slider = UnifiedSlider(min=0, max=100, mode='range', size_hint_y=None, height=dp_scaled(35))
        self.hum_slider.bind(min_value=self._on_env_slider_change, max_value=self._on_env_slider_change,
                             on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.hum_slider)

        self.lbl_vpd = self._add_slider_label("VPD TARGET", "0.8 - 1.5")
        self.vpd_slider = UnifiedSlider(min=8, max=15, range_min=0, range_max=30, mode='range', 
                                      size_hint_y=None, height=dp_scaled(35))
        self.vpd_slider.bind(min_value=self._on_vpd_slider_change, max_value=self._on_vpd_slider_change,
                             on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.vpd_slider)

        self.panel.add_widget(Widget())

        # Buttons
        btn_row = BoxLayout(size_hint_y=None, height=dp_scaled(40), spacing=dp_scaled(10))
        self.btn_man = self._create_styled_btn("MANUAL")
        self.btn_auto = self._create_styled_btn("AUTOMATIC")
        self.btn_chao = self._create_styled_btn("CHAOTIC")
        
        self.btn_man.bind(on_release=lambda *_: self._set_mode("man"))
        self.btn_auto.bind(on_release=lambda *_: self._set_mode("auto"))
        self.btn_chao.bind(on_release=lambda *_: self._set_mode("chao"))
        
        btn_row.add_widget(self.btn_man)
        btn_row.add_widget(self.btn_auto)
        btn_row.add_widget(self.btn_chao)
        self.panel.add_widget(btn_row)

        # Lock & Events
        self.lock_overlay = LockOverlay(parent=self, panel=self.panel, unlock_callback=self._on_unlock)
        Clock.schedule_once(lambda dt: self.lock_overlay.create(), 0.3)
        
        self._update_event = Clock.schedule_interval(self.update_ui, 1.0)
        self._sync_event = Clock.schedule_interval(self._sync_to_client, 1.3)
        
        Clock.schedule_once(self._init_values, 0.1)
        self.add_widget(self.panel)

    # ===================================================================
    # ZENTRALE SEND-METHODE MIT AUTO-RETRY
    # ===================================================================
    def _send_current_state(self, is_retry=False, **kwargs):
        """Sendet den kompletten aktuellen Zustand (alle Slider + Modus)"""
        if not self._init_done:
            return

        mode = kwargs.get("mode", self._target_mode)

        rev = GLOBAL_STATE.send_overlay_command(
            "exhaust_fan",
            min=int(self.range_slider.min_value),
            max=int(self.range_slider.max_value),
            t_min=int(self.temp_slider.min_value),
            t_max=int(self.temp_slider.max_value),
            h_min=int(self.hum_slider.min_value),
            h_max=int(self.hum_slider.max_value),
            vpd_min=round(self.vpd_slider.min_value / 10.0, 1),
            vpd_max=round(self.vpd_slider.max_value / 10.0, 1),
            mode=mode
        )

        if rev:
            self._last_sent_rev = rev
            self._last_send_time = time.time()
            self.sync_icon.color = (1, 0.5, 0, 1)

            if not is_retry:
                self._retry_count = 0   # Nur echte User-Aktion setzt Retry-Zähler zurück

    # ===================================================================
    # UPDATE_UI mit starkem Auto-Retry
    # ===================================================================
    def update_ui(self, *_):
        mac = GLOBAL_STATE.get_active_device_id()
        server_data = GLOBAL_STATE.overlay_engine.get_latest_device_data(mac)
        if not server_data: 
            return

        # SESSION CHECK
        current_init_rev = int(server_data.get('rev_init_exhaust', 0))
        if not hasattr(self, "_last_adopted_init") or self._last_adopted_init != current_init_rev:
            self._last_adopted_init = current_init_rev
            return

        server_rev = int(server_data.get('rev_exhaust', 0))
        last_sent = getattr(self, '_last_sent_rev', 0)
        time_since_action = time.time() - self._last_user_action

        pending = last_sent > server_rev
        is_synced = (not pending) and not self._user_active and (time_since_action > 1.8)

        # === AUTO-RETRY LOGIK ===
        if pending and (time.time() - self._last_send_time > 3.0):
            if self._retry_count < self._max_retries:
                self._retry_count += 1
                print(f"[Exhaust] NETWORK TIMEOUT → Resend Rev {last_sent} (Retry {self._retry_count}/{self._max_retries})")
                self._send_current_state(is_retry=True)
                return
            else:
                print(f"[Exhaust] MAX RETRIES ({self._max_retries}) reached for Rev {last_sent}")

        # Live-Werte immer aktualisieren
        self.lbl_rpm.text = f"RPM: {int(server_data.get('exhaust_fan_rpm', 0))}"
        self.lbl_live_speed.text = f"LIVE: {int(server_data.get('exhaust_fan_speed_now', 0))}%"

        # Status Icon
        if not is_synced:
            if pending and self._retry_count >= self._max_retries:
                self.sync_icon.text = "[font=FA]\uf071[/font]"   # Warning Icon
                self.sync_icon.color = (1, 0.3, 0, 1)
            else:
                self.sync_icon.text = "[font=FA]\uf021[/font]"
                self.sync_icon.color = (1, 0.5, 0, 1)
            return

        # === SYNCED ===
        self._retry_count = 0
        self.sync_icon.text = "[font=FA]\uf058[/font]"
        self.sync_icon.color = (0, 1, 0, 1)

        if not self._user_active:
            self._ui_lock = True
            self._apply_server_snapshot(server_data)
            self._ui_lock = False

    def _apply_server_snapshot(self, data):
        s_min = int(data.get('exhaust_fan_min', 20))
        s_max = int(data.get('exhaust_fan_pct', 65))
        s_mode = data.get('exhaust_fan_mode', 'auto')

        t_min = int(data.get('target_temp_min', 22))
        t_max = int(data.get('target_temp_max', 28))
        h_min = int(data.get('target_humidity_min', 40))
        h_max = int(data.get('target_humidity_max', 70))

        v_min = float(data.get('target_vpd_min', 0.8))
        v_max = float(data.get('target_vpd_max', 1.5))

        self._ui_lock = True

        self.range_slider.max_value = s_max
        self.range_slider.min_value = s_min
        self.temp_slider.max_value = t_max
        self.temp_slider.min_value = t_min
        self.hum_slider.max_value = h_max
        self.hum_slider.min_value = h_min
        self.vpd_slider.max_value = int(v_max * 10)
        self.vpd_slider.min_value = int(v_min * 10)

        self._ui_lock = False

        self.lbl_val.text = f"{s_min}% - {s_max}%"
        self.lbl_temp.text = f"{t_min}° - {t_max}°"
        self.lbl_hum.text = f"{h_min}% - {h_max}%"
        self.lbl_vpd.text = f"{v_min:.1f} - {v_max:.1f}"

        self._apply_button_styles(s_mode)
        self._target_mode = s_mode
        self._last_sent_rev = int(data.get('rev_exhaust', 0))

    # ===================================================================
    # Weitere Methoden
    # ===================================================================
    def _add_slider_label(self, left_text, right_text=""):
        row = BoxLayout(size_hint_y=None, height=dp_scaled(15))
        row.add_widget(Label(text=left_text, font_size=sp_scaled(13), color=(0,1,0,0.5), halign="left"))
        lbl_right = Label(text=right_text, font_size=sp_scaled(13), color=(1,1,1,0.6), halign="right")
        row.add_widget(lbl_right)
        self.panel.add_widget(row)
        return lbl_right

    def _create_styled_btn(self, text):
        return Button(text=text, markup=True, background_normal="", 
                      background_color=(0.15, 0.15, 0.15, 1),
                      color=(0.5, 0.5, 0.5, 1), font_size=sp_scaled(14))

    def _set_mode(self, mode):
        if self._locked: 
            return
        self._target_mode = mode
        self._send_current_state()          # User-Aktion

    def _on_slider_change(self, *args):
        if not self._init_done or self._ui_lock or self._locked: 
            return
        self.lbl_val.text = f"{int(self.range_slider.min_value)}% - {int(self.range_slider.max_value)}%"
        self.sync_icon.color = (1, 0.5, 0, 1)

    def _on_env_slider_change(self, *args):
        if not self._init_done or self._ui_lock or self._locked: 
            return
        self.lbl_temp.text = f"{int(self.temp_slider.min_value)}° - {int(self.temp_slider.max_value)}°"
        self.lbl_hum.text = f"{int(self.hum_slider.min_value)}% - {int(self.hum_slider.max_value)}%"
        self.sync_icon.color = (1, 0.5, 0, 1)

    def _on_vpd_slider_change(self, *args):
        if not self._init_done or self._ui_lock or self._locked: 
            return
        self.lbl_vpd.text = f"{self.vpd_slider.min_value/10.0:.1f} - {self.vpd_slider.max_value/10.0:.1f}"
        self.sync_icon.color = (1, 0.5, 0, 1)

    def _touch_down(self, instance, touch):
        if self._locked: return False
        if instance.collide_point(*touch.pos):
            self._user_active = True
            return False

    def _touch_up(self, instance, touch):
        if self._user_active:
            self._user_active = False
            self._last_user_action = time.time()
            self._send_current_state()          # User-Aktion → Retry-Zähler zurück
            return False

    def _force_sync(self, *_):
        self._send_current_state()

    def _apply_button_styles(self, mode):
        c_bg = (0.15, 0.15, 0.15, 1)
        self.btn_man.background_color  = (0, 1, 0, 0.8) if mode == "man" else c_bg
        self.btn_auto.background_color = (0, 0.7, 1, 0.8) if mode == "auto" else c_bg
        self.btn_chao.background_color = (1, 0.5, 0, 0.8) if mode == "chao" else c_bg

    def _init_values(self, *_):
        mac = GLOBAL_STATE.get_active_device_id()
        data = GLOBAL_STATE.overlay_engine.get_buffer_data(mac)
    
        if not data:
            Clock.schedule_once(self._init_values, 0.3)
            return
    
        # === 1. WERTE HOLEN ===
        s_min = int(data.get("exhaust_fan_min", 20))
        s_max = int(data.get("exhaust_fan_pct", 65))
        s_mode = data.get("exhaust_fan_mode", "auto")
    
        t_min = int(data.get("target_temp_min", 22))
        t_max = int(data.get("target_temp_max", 28))
    
        h_min = int(data.get("target_humidity_min", 40))
        h_max = int(data.get("target_humidity_max", 70))
    
        v_min = float(data.get("target_vpd_min", 0.8))
        v_max = float(data.get("target_vpd_max", 1.5))
    
        # === 2. UI LOCK (WICHTIG!) ===
        self._ui_lock = True
    
        # --- SPEED ---
        self.range_slider.max_value = s_max
        self.range_slider.min_value = s_min
    
        # --- TEMP ---
        self.temp_slider.max_value = t_max
        self.temp_slider.min_value = t_min
    
        # --- HUM ---
        self.hum_slider.max_value = h_max
        self.hum_slider.min_value = h_min
    
        # --- VPD ---
        self.vpd_slider.max_value = int(v_max * 10)
        self.vpd_slider.min_value = int(v_min * 10)
    
        # === UNLOCK ===
        self._ui_lock = False
    
        # === 3. LABELS (EXPLIZIT!) ===
        self.lbl_val.text = f"{s_min}% - {s_max}%"
        self.lbl_temp.text = f"{t_min}° - {t_max}°"
        self.lbl_hum.text = f"{h_min}% - {h_max}%"
        self.lbl_vpd.text = f"{v_min:.1f} - {v_max:.1f}"
    
        # === 4. BUTTONS ===
        self._apply_button_styles(s_mode)
    
        # === 5. STATE + RETRY-SYSTEM INITIALISIERUNG ===
        self._target_mode = s_mode
        self._last_sent_rev = int(data.get("rev_exhaust", 0))
        self._last_send_time = 0          # Wichtig für Timeout-Logik
        self._retry_count = 0             # Retry-Zähler zurücksetzen
    
        # === 6. FINALIZE ===
        self._init_done = True
    
        # Slider freigeben
        self.range_slider.disabled = False
        self.temp_slider.disabled = False
        self.hum_slider.disabled = False
        self.vpd_slider.disabled = False
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

    def _on_unlock(self):
        self._locked = False
        for s in [self.range_slider, self.temp_slider, self.hum_slider, self.vpd_slider]:
            s.disabled = False

    def _u(self, *_):
        self.bg_rect.pos = self.panel.pos
        self.bg_rect.size = self.panel.size
        self.outline.rounded_rectangle = (self.panel.x, self.panel.y, self.panel.width, self.panel.height, dp_scaled(20))

    def close(self):
        if hasattr(self, '_update_event') and self._update_event:
            self._update_event.cancel()
        if hasattr(self, '_sync_event') and self._sync_event:
            self._sync_event.cancel()
        if self.parent:
            self.parent.remove_widget(self)
        GLOBAL_STATE.ui_handler.active_exhaust_fan_overlay = None