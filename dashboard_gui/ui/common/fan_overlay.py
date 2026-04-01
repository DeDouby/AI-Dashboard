from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.clock import Clock
import config 
import time 
import json 
import os
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled

# WICHTIG: Den globalen Client importieren
from web_client import WEB_CLIENT 

class FanOverlay(FloatLayout):
    def __init__(self, parent_header, **kwargs):
        super().__init__(**kwargs)
        self.parent_header = parent_header
        self._pending_updates = {} 
        self._user_active = False 
        self._last_user_action = 0 
        self._init_done = False
        self.sync_path = os.path.join(config.DATA, "settings_sync.json")

        # Intervalle für UI-Refresh und Server-Abgleich
        self._update_event = Clock.schedule_interval(self.update_ui, 1.0)
        self._sync_event = Clock.schedule_interval(self._sync_to_client, 1.3)

        # 1. Hintergrund-Abdunkelung
        bg = Button(background_color=(0, 0, 0, 0.25))
        bg.bind(on_release=lambda *_: self.close())
        self.add_widget(bg)

        # 2. Das Haupt-Panel
        self.panel = BoxLayout(
            orientation="vertical", 
            padding=dp_scaled(20), 
            spacing=dp_scaled(12),
            size_hint=(None, None), 
            size=(dp_scaled(320), dp_scaled(450)),
            pos_hint={"right": 0.98, "top": 0.98}
        )

        with self.panel.canvas.before:
            Color(0, 0, 0, 0.65)
            self.bg_rect = RoundedRectangle(radius=[dp_scaled(20)])
            Color(0, 1, 0, 0.4)
            self.outline = Line(width=1.2)

        self.panel.bind(pos=self._u, size=self._u)

        # --- TITEL-ZEILE MIT SYNC-BUTTON ---
        title_row = BoxLayout(size_hint_y=None, height=dp_scaled(30), spacing=dp_scaled(5))
        self.lbl_title = Label(
            text="FAN CONTROL PRO", 
            bold=True, color=(0, 1, 0, 1),
            font_size=sp_scaled(16),
            halign="left"
        )
        
        self.sync_icon = Button(
            text="[font=FA]\uf021[/font]",
            markup=True,
            font_size=sp_scaled(26),
            size_hint_x=None, width=dp_scaled(40),
            size_hint_y=None, height=dp_scaled(40),
            background_normal="", background_color=(0, 0, 0, 0)
        )
        self.sync_icon.bind(on_release=self._force_sync)
        
        title_row.add_widget(self.lbl_title)
        title_row.add_widget(self.sync_icon)
        self.panel.add_widget(title_row)

        # --- WERTE-ANZEIGE ---
        self.lbl_val = Label(text="0% - 0%", font_size=sp_scaled(38), bold=True)
        self.panel.add_widget(self.lbl_val)
        
        self.lbl_rpm = Label(text="RPM: 0", font_size=sp_scaled(18), color=(0.7, 0.7, 1, 1))
        self.panel.add_widget(self.lbl_rpm)

        # MAX SLIDER
        self.panel.add_widget(Label(text="MAX SPEED", font_size=sp_scaled(11), color=(0,1,0,0.5), size_hint_y=None, height=dp_scaled(15)))
        self.slider_max = Slider(min=0, max=100, step=1, size_hint_y=None, height=dp_scaled(35))
        self.slider_max.bind(value=self._on_slider_change, on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.slider_max)
        
        # MIN SLIDER
        self.panel.add_widget(Label(text="MIN SPEED", font_size=sp_scaled(11), color=(0,1,0,0.5), size_hint_y=None, height=dp_scaled(15)))
        self.slider_min = Slider(min=0, max=100, step=1, size_hint_y=None, height=dp_scaled(35))
        self.slider_min.bind(value=self._on_slider_change, on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.slider_min)

        # Modi-Buttons
        btn_row = BoxLayout(size_hint_y=None, height=dp_scaled(45), spacing=dp_scaled(10))
        self.btn_man = self._create_styled_btn("MANUAL")
        self.btn_nat = self._create_styled_btn("NATURAL")
        self.btn_chao = self._create_styled_btn("CHAOTIC")
        
        self.btn_man.bind(on_release=lambda *_: self._set_mode("man"))
        self.btn_nat.bind(on_release=lambda *_: self._set_mode("nat"))
        self.btn_chao.bind(on_release=lambda *_: self._set_mode("chao"))
        
        btn_row.add_widget(self.btn_man); btn_row.add_widget(self.btn_nat); btn_row.add_widget(self.btn_chao)
        self.panel.add_widget(btn_row)

        btn_close = Button(
            text="FERTIG",
            size_hint_y=None, height=dp_scaled(45),
            background_normal="", background_color=(0.2, 0.2, 0.2, 1),
            bold=True
        )
        btn_close.bind(on_release=lambda *_: self.close())
        self.panel.add_widget(btn_close)
        
        Clock.schedule_once(self._init_values, 0)
        self.add_widget(self.panel)

    def _create_styled_btn(self, text):
        return Button(text=text, background_normal="", background_color=(0.2, 0.2, 0.2, 1), 
                      bold=True, font_size=sp_scaled(10))

    def _on_slider_change(self, instance, value):
            if not self._init_done: return
            
            # 1. Logik: Min darf nie größer als Max sein
            if self.slider_min.value > self.slider_max.value:
                if instance == self.slider_min: self.slider_max.value = value
                else: self.slider_min.value = value
                
            self.lbl_val.text = f"{int(self.slider_min.value)}% - {int(self.slider_max.value)}%"
            
            # 2. Sofort-Feedback für das Icon (Orange = Arbeitet)
            self.sync_icon.text = "[font=FA]\uf021[/font]"
            self.sync_icon.color = (1, 0.5, 0, 1)
    
            mac = GLOBAL_STATE.get_active_device_id()
            if mac:
                new_rev = int(time.time())
                self._last_sent_rev = new_rev # Merken für den Vergleich in update_ui
                
                # 3. DAS IST DER FIX: Direktes Senden wie im Light-Modul
                WEB_CLIENT.send_control(mac, {
                    "fan_pct": int(self.slider_max.value),
                    "fan_min": int(self.slider_min.value),
                    "rev": new_rev
                })
                
                # 4. Optional: Trotzdem lokal in die Datei sichern
                self._pending_updates.update({
                    "fan_pct": int(self.slider_max.value),
                    "fan_min": int(self.slider_min.value),
                    "rev": new_rev
                })
                self._last_user_action = time.time()

    def _force_sync(self, *_):
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac: return
        try:
            with open(self.sync_path, "r") as f:
                data = json.load(f).get(mac, {})
            payload = {
                "fan_pct": data.get("fan_pct", 0),
                "fan_min": data.get("fan_min", 0),
                "fan_mode": data.get("fan_mode", "man"),
                "rev": int(time.time())
            }
            WEB_CLIENT.send_control(mac, payload)
            self.sync_icon.color = (1, 1, 0, 1)
        except: pass

# --- ZUSÄTZLICHE OPTIMIERUNG DER UPDATE-LOGIK ---
    def update_ui(self, *_):
        if not getattr(WEB_CLIENT, "ready", False) or not self._init_done:
            return
        
        now = time.time()
        # WICHTIG: Erhöhe die Sperre auf 3 Sekunden nach einer User-Aktion (Slider/Button)
        if self._user_active or (now - self._last_user_action < 3.0):
            return
        
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac: return

        server_data = WEB_CLIENT.current_data.get(mac)
        if not server_data: return

        server_rev = int(server_data.get('rev', 0))
        last_sent = getattr(self, '_last_sent_rev', 0)

        # --- SYNC CHECK ---
        # Wenn der Server eine kleinere Revision hat als unser letzter Befehl,
        # ignorieren wir den Rest des Updates komplett.
        if server_rev < last_sent:
            self.sync_icon.text = "[font=FA]\uf021[/font]"
            self.sync_icon.color = (1, 0.5, 0, 1)
            sync_pending = True
        else:
            self.sync_icon.text = "[font=FA]\uf058[/font]"
            self.sync_icon.color = (0, 1, 0, 1)
            sync_pending = False

        # --- WERTE ÜBERNEHMEN ---
        arduino_mode = server_data.get('fan_mode', 'man')
        arduino_min = server_data.get('fan_min', 0)
        arduino_max = server_data.get('fan_pct', 0)

        # Slider nur bewegen, wenn sie sich wirklich geändert haben
        if abs(self.slider_min.value - arduino_min) > 0.5:
            self.slider_min.value = arduino_min
        if abs(self.slider_max.value - arduino_max) > 0.5:
            self.slider_max.value = arduino_max
            
        self.lbl_val.text = f"{int(arduino_min)}% - {int(arduino_max)}%"
        self.lbl_rpm.text = f"RPM: {server_data.get('rpm', 0)}"

        # --- BUTTONS ÜBERNEHMEN ---
        # Hier lag der Fehler: Jetzt erst werden die Buttons basierend auf den SERVER-Daten gefärbt
        if not sync_pending:
            self.btn_man.background_color = (0, 1, 0, 0.6) if arduino_mode == "man" else (0.2, 0.2, 0.2, 1)
            self.btn_nat.background_color = (0, 0.7, 1, 0.6) if arduino_mode == "nat" else (0.2, 0.2, 0.2, 1)
            self.btn_chao.background_color = (1, 0.2, 0.2, 0.6) if arduino_mode == "chao" else (0.2, 0.2, 0.2, 1)
            
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

    def _set_mode(self, mode):      
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac: return
        
        now = time.time()
        new_rev = int(now)
        self._last_sent_rev = new_rev # WICHTIG: Revision registrieren!
        self._last_user_action = now  # Sperrt das Update_UI für 2 Sekunden

        # 1. Sofort-Feedback für die UI (Farbe direkt umschalten)
        self.btn_man.background_color = (0, 1, 0, 0.6) if mode == "man" else (0.2, 0.2, 0.2, 1)
        self.btn_nat.background_color = (0, 0.7, 1, 0.6) if mode == "nat" else (0.2, 0.2, 0.2, 1)
        self.btn_chao.background_color = (1, 0.2, 0.2, 0.6) if mode == "chao" else (0.2, 0.2, 0.2, 1)
        
        # Icon auf Orange (Sync läuft)
        self.sync_icon.text = "[font=FA]\uf021[/font]"
        self.sync_icon.color = (1, 0.5, 0, 1)

        # 2. Ab zum ESP32
        payload = {
            "fan_pct": int(self.slider_max.value),
            "fan_min": int(self.slider_min.value),
            "fan_mode": mode,
            "rev": new_rev
        }
        WEB_CLIENT.send_control(mac, payload)
        
        # 3. Backup in Datei (optional)
        self._pending_updates.update({"fan_mode": mode, "rev": new_rev})
        self._sync_to_client(0)
    def _touch_down(self, slider, touch):
        if slider.collide_point(*touch.pos): self._user_active = True

    def _touch_up(self, slider, touch):
        if slider.collide_point(*touch.pos): 
            self._user_active = False
            self._last_user_action = time.time()

    def _u(self, *_):
        self.bg_rect.pos = self.panel.pos
        self.bg_rect.size = self.panel.size
        self.outline.rounded_rectangle = (self.panel.x, self.panel.y, self.panel.width, self.panel.height, dp_scaled(20))

    def close(self):
        if self._update_event: self._update_event.cancel()
        if self._sync_event: self._sync_event.cancel()
        if self.parent: self.parent.remove_widget(self)
        GLOBAL_STATE.ui_handler.active_fan_overlay = None

    def _init_values(self, *_):
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac: return
    
        # 1. Defaults setzen (gegen Crash & UnboundLocalError)
        saved_min = 0
        saved_max = 0
        saved_mode = "man"

        # 2. Lokalen Stand laden
        if os.path.exists(self.sync_path):
            try:
                with open(self.sync_path, "r") as f:
                    all_data = json.load(f)
                    data = all_data.get(mac, {})
                    # Werte extrahieren oder bei 0 bleiben
                    saved_min = data.get("fan_min", 0)
                    saved_max = data.get("fan_pct", 0)
                    saved_mode = data.get("fan_mode", "man")
            except Exception as e:
                print(f"[Fan-UI] Init Read Error: {e}")

        # 3. UI Werte setzen (Slider & Labels)
        self.slider_min.value = saved_min
        self.slider_max.value = saved_max
        self.lbl_val.text = f"{int(saved_min)}% - {int(saved_max)}%"
        
        # Buttons initial einfärben
        # Buttons initial KORREKT einfärben (Farben passend zum Modus)
        self.btn_man.background_color = (0, 1, 0, 0.6) if saved_mode == "man" else (0.2, 0.2, 0.2, 1)
        self.btn_nat.background_color = (0, 0.7, 1, 0.6) if saved_mode == "nat" else (0.2, 0.2, 0.2, 1)
        self.btn_chao.background_color = (1, 0.2, 0.2, 0.6) if saved_mode == "chao" else (0.2, 0.2, 0.2, 1)

        self._init_done = True

        # --- DER TRICK: MASTER-AUTO-SYNC ---
        # Wir triggern den Force-Sync automatisch 0.1s nach dem Start an.
        # Das sorgt dafür, dass das Handy seine Revision an den ESP32 drückt
        # und das Icon danach sofort GRÜN wird.
        Clock.schedule_once(lambda dt: self._force_sync(), 0.2)
        print(f"[Fan-UI] Auto-Button-Sync triggered for {mac}")