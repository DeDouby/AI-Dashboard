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


class CirculationFanOverlay(FloatLayout):
    def __init__(self, parent_header, **kwargs):
        super().__init__(**kwargs)
        self.parent_header = parent_header
        self._pending_updates = {} 
        self._user_active = False 
        self._last_user_action = 0 
        self._init_done = False
        self.sync_path = os.path.join(config.DATA, "settings_sync.json")
        
        # === NEU: GUTER AUTO-RETRY MECHANISMUS ===
        self._last_sent_rev = 0
        self._last_send_time = 0
        self._retry_count = 0
        self._max_retries = 5

        self._update_event = Clock.schedule_interval(self.update_ui, 1.0)
        self._sync_event = Clock.schedule_interval(self._sync_to_client, 1.3)
        
        self._locked = True
        self._target_mode = "nat"
        self._ui_lock = False
        
        self._target_state = {"min": 20, "max": 65, "mode": "nat"}

        # Hintergrund
        bg = Button(background_color=(0, 0, 0, 0.25))
        bg.bind(on_release=lambda *_: self.close())
        self.add_widget(bg)

        # Panel
        self.panel = BoxLayout(
            orientation="vertical", 
            spacing=dp_scaled(10),
            size_hint=(None, None), 
            size=(dp_scaled(420), dp_scaled(440)),
            padding=[dp_scaled(25), dp_scaled(15), dp_scaled(25), dp_scaled(25)], 
            pos_hint={"right": 0.98, "top": 0.98}
        )

        with self.panel.canvas.before:
            Color(0, 0, 0, 0.75)
            self.bg_rect = RoundedRectangle(radius=[dp_scaled(20)])
            Color(0, 1, 0, 0.3)
            self.outline = Line(width=1.2)

        self.panel.bind(pos=self._u, size=self._u)

        # Titel + Sync Icon
        title_row = BoxLayout(size_hint_y=None, height=dp_scaled(40), spacing=dp_scaled(5))
        self.lbl_title = Label(text="CIRCULATION FAN CONTROL", bold=True, color=(0, 1, 0, 1),
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

        self.panel.add_widget(Widget(size_hint_y=None, height=dp_scaled(5)))

        self.lbl_val = Label(text="0% - 0%", font_size=sp_scaled(36), bold=True, 
                             size_hint_y=None, height=dp_scaled(50))
        self.panel.add_widget(self.lbl_val)

        info_row = BoxLayout(size_hint_y=None, height=dp_scaled(25))
        self.lbl_rpm = Label(text="RPM: 0", font_size=sp_scaled(15), color=(0.7, 0.7, 1, 0.8))
        self.lbl_live_speed = Label(text="LIVE: 0%", font_size=sp_scaled(15), bold=True, color=(0, 1, 1, 0.8))
        info_row.add_widget(self.lbl_rpm)
        info_row.add_widget(self.lbl_live_speed)
        self.panel.add_widget(info_row)

        self.panel.add_widget(Widget(size_hint_y=None, height=dp_scaled(15)))

        self.panel.add_widget(Label(text="SPEED RANGE (MIN - MAX)", 
                                  font_size=sp_scaled(15), color=(0,1,0,0.5), 
                                  size_hint_y=None, height=dp_scaled(15)))
        
        self.range_slider = UnifiedSlider(min=0, max=100, mode='range', 
                                        size_hint_y=None, height=dp_scaled(50))
        self.range_slider.bind(min_value=self._on_slider_change, max_value=self._on_slider_change,
                             on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.range_slider)

        self.panel.add_widget(Widget())

        # Modi Buttons
        btn_row = BoxLayout(size_hint_y=None, height=dp_scaled(40), spacing=dp_scaled(10))
        self.btn_man = self._create_styled_btn("MANUAL")
        self.btn_nat = self._create_styled_btn("NATURAL")
        self.btn_chao = self._create_styled_btn("CHAOTIC")
        btn_row.add_widget(self.btn_man)
        btn_row.add_widget(self.btn_nat)
        btn_row.add_widget(self.btn_chao)
        self.panel.add_widget(btn_row)

        self.btn_man.bind(on_release=lambda *_: self._set_mode("man"))
        self.btn_nat.bind(on_release=lambda *_: self._set_mode("nat"))
        self.btn_chao.bind(on_release=lambda *_: self._set_mode("chao"))

        Clock.schedule_once(self._init_values, 0)
        
        self.lock_overlay = LockOverlay(parent=self, panel=self.panel, unlock_callback=self._on_unlock)
        Clock.schedule_once(lambda dt: self.lock_overlay.create(), 0.4)
        
        self.add_widget(self.panel)

    # =========================================================================
    # AUTO-RETRY SEND LOGIK (zentralisiert)
    # =========================================================================
    def _send_current_state(self, is_retry=False, **kwargs):
        """Einheitliche Sende-Methode mit Retry-Unterstützung"""
        if not self._init_done:
            return

        mode = kwargs.get("mode", self._target_state["mode"])

        new_rev = GLOBAL_STATE.send_overlay_command(
            "circulation_fan",
            min=int(self.range_slider.min_value),
            max=int(self.range_slider.max_value),
            mode=mode
        )

        if new_rev:
            self._last_sent_rev = new_rev
            self._last_send_time = time.time()
            self._set_orange()

            if not is_retry:
                self._retry_count = 0   # Nur echte User-Aktion setzt Zähler zurück


    # =========================================================================
    # UPDATE_UI mit starkem Auto-Retry
    # =========================================================================
    def update_ui(self, *_):
        mac = GLOBAL_STATE.get_active_device_id()
        server_data = GLOBAL_STATE.overlay_engine.get_buffer_data(mac)
        if not server_data: 
            return

        # === 1. HANDSHAKE & SESSION CHECK ===
        server_init = server_data.get('rev_init_circfan', 0)
        server_rev = int(server_data.get('rev_circfan', 0))
        
        # Das ist das Herzstück: Hat der ESP meinen Ping gespiegelt?
        is_alive = (server_init == self._my_handshake_id)
        
        # Falls der ESP neu gestartet ist (neue Session-ID vom ESP):
        if not hasattr(self, "_last_adopted_init") or self._last_adopted_init != server_init:
            self._last_adopted_init = server_init
            # Wenn der ESP rebootet, müssen wir unsere Revs angleichen
            if not is_alive: 
                self._last_sent_rev = server_rev
            return 

        # === 2. STATUS ANALYSE ===
        last_sent = getattr(self, '_last_sent_rev', 0)
        time_since_action = time.time() - self._last_user_action

        # Revisionen abgleichen
        pending = last_sent > server_rev
        
        # Nur Grün wenn: Handshake OK + Keine Rev ausstehend + User fertig + Zeit rum
        is_synced = is_alive and (not pending) and not self._user_active and (time_since_action > 1.5)

        # === 3. AUTO RETRY LOGIK ===
        if pending and (time.time() - self._last_send_time > 3.0):
            if self._retry_count < self._max_retries:
                self._retry_count += 1
                self._send_current_state(is_retry=True)
                return

        # Live-Werte immer anzeigen
        self.lbl_rpm.text = f"RPM: {int(server_data.get('circulation_fan_rpm', 0))}"
        self.lbl_live_speed.text = f"LIVE: {int(server_data.get('circulation_fan_speed_now', 0))}%"

# === 4. ICON LOGIK (Der ehrliche Status) ===
        if not is_synced:
            # Wenn nicht alive (Handshake fehlt) ODER pending (Befehl unterwegs) -> Orange
            self.sync_icon.text = "[font=FA]\uf021[/font]" 
            self.sync_icon.color = (1, 0.5, 0, 1)
            
            # Spezialfall: Timeout nach Max Retries -> Rot
            if pending and self._retry_count >= self._max_retries:
                self.sync_icon.text = "[font=FA]\uf071[/font]"
                self.sync_icon.color = (1, 0.3, 0, 1)
            return

        # === ALLES OK (Grüner Haken) ===
        self._retry_count = 0
        self.sync_icon.text = "[font=FA]\uf058[/font]"
        self.sync_icon.color = (0, 1, 0, 1)

        # UI-Werte vom ESP übernehmen (nur wenn User gerade nicht schiebt)
        if not self._user_active:
            self._ui_lock = True
            self.range_slider.min_value = int(server_data.get('circulation_fan_min', 20))
            self.range_slider.max_value = int(server_data.get('circulation_fan_pct', 65))
            self._ui_lock = False
            self.lbl_val.text = f"{int(self.range_slider.min_value)}% - {int(self.range_slider.max_value)}%"
            self._apply_button_styles(server_data.get('circulation_fan_mode', 'nat'))

    def _on_slider_change(self, instance, value):
        if not self._init_done or self._ui_lock: 
            return
        min_v = int(self.range_slider.min_value)
        max_v = int(self.range_slider.max_value)
        self.lbl_val.text = f"{min_v}% - {max_v}%"
        self._target_state["min"] = min_v
        self._target_state["max"] = max_v
        self._set_orange()

    def _set_mode(self, mode):
        if self._locked: 
            return
        self._target_state["mode"] = mode
        self._send_current_state()          # User-Aktion → is_retry=False

    def _touch_up(self, instance, touch):
        if self._locked or not self._user_active:
            return False
        self._user_active = False
        self._last_user_action = time.time()
        self._send_current_state()          # User-Aktion
        return False

    def _touch_down(self, instance, touch):
        if self._locked:
            return False
        if instance.collide_point(*touch.pos):
            self._user_active = True
            return False

    def _force_sync(self, *_):
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac:
            return
    
        # 1. NEUE SESSION ID
        self._my_handshake_id = int(time.time())
    
        # 2. HANDSHAKE SENDEN (RAM ONLY)
        GLOBAL_STATE.overlay_engine.send_fan_handshake(mac, self._my_handshake_id)
    
        # 3. OPTIONAL: State direkt pushen
        self._send_current_state()

    def _set_orange(self):
        self.sync_icon.text = "[font=FA]\uf021[/font]"
        self.sync_icon.color = (1, 0.5, 0, 1)

    # Rest bleibt fast unverändert (nur kleine Cleanups)
    def _create_styled_btn(self, text):
        return Button(text=text, markup=True, background_normal="",
                      background_color=(0.15, 0.15, 0.15, 1),
                      color=(0.5, 0.5, 0.5, 1), font_size=sp_scaled(15))

    def _apply_button_styles(self, mode):
        c_bg = (0.15, 0.15, 0.15, 1)
        self.btn_man.background_color  = (0, 1, 0, 0.8) if mode == "man" else c_bg
        self.btn_nat.background_color  = (0, 0.6, 1, 0.8) if mode == "nat" else c_bg
        self.btn_chao.background_color = (1, 0.5, 0, 0.8) if mode == "chao" else c_bg
        
        self.btn_man.color  = (1,1,1,1) if mode == "man" else (0.6,0.6,0.6,1)
        self.btn_nat.color  = (1,1,1,1) if mode == "nat" else (0.6,0.6,0.6,1)
        self.btn_chao.color = (1,1,1,1) if mode == "chao" else (0.6,0.6,0.6,1)

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
            with open(tmp_path, "w") as f: 
                json.dump(data, f)
            os.replace(tmp_path, self.sync_path)
            self._pending_updates.clear()
        except: 
            pass

    def _init_values(self, *_):
        mac = GLOBAL_STATE.get_active_device_id()
        data = GLOBAL_STATE.overlay_engine.get_buffer_data(mac)
        if not data:
            Clock.schedule_once(self._init_values, 0.3)
            return

        # 1. ZUERST die ID erstellen (Wichtig: Vor dem Senden!)
        self._my_handshake_id = int(time.time())
        
        # 2. DANACH die ID an die Engine übergeben
        GLOBAL_STATE.overlay_engine.send_fan_handshake(mac, self._my_handshake_id)
        
        # --- Rest der Initialisierung ---
        srv_min = data.get("circulation_fan_min", 20)
        srv_max = data.get("circulation_fan_pct", 65)
        srv_mode = data.get("circulation_fan_mode", "nat")
        
        self._ui_lock = True
        self.range_slider.min_value = srv_min
        self.range_slider.max_value = srv_max
        self._ui_lock = False

        self._target_state["mode"] = srv_mode
        self.lbl_val.text = f"{int(srv_min)}% - {int(srv_max)}%"
        self._apply_button_styles(srv_mode)

        self._last_sent_rev = data.get('rev_circfan', 0)
        self._retry_count = 0
        self._last_send_time = 0
        self._init_done = True
        self.range_slider.disabled = False

    def _on_unlock(self):
        self._locked = False
        self.range_slider.disabled = False

    def _u(self, *_):
        self.bg_rect.pos = self.panel.pos
        self.bg_rect.size = self.panel.size
        self.outline.rounded_rectangle = (self.panel.x, self.panel.y, self.panel.width, self.panel.height, dp_scaled(20))

    def close(self):
        if self._update_event: self._update_event.cancel()
        if self._sync_event:   self._sync_event.cancel()
        if self.parent: self.parent.remove_widget(self)
        GLOBAL_STATE.ui_handler.active_circulation_fan_overlay = None