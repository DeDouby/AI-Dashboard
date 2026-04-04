from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ReferenceListProperty
from kivy.graphics import Color, RoundedRectangle, Ellipse
import config 
import time 
import json 
import os
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled

# WICHTIG: Den globalen Client importieren
from web_client import WEB_CLIENT 

class RangeSlider(Widget):
    min_value = NumericProperty(0)
    max_value = NumericProperty(100)
    range_min = NumericProperty(0)
    range_max = NumericProperty(100)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._update_canvas, size=self._update_canvas, 
                  min_value=self._update_canvas, max_value=self._update_canvas)

    def _update_canvas(self, *args):
        self.canvas.after.clear()
    
        # Größenparameter (EASY später tweakbar)
        track_h = 10
        active_h = 14
        handle_size = 34
    
        with self.canvas.after:
            # =====================
            # 1. BACK TRACK
            # =====================
            Color(0.15, 0.15, 0.15, 1)
            RoundedRectangle(
                pos=(self.x, self.center_y - track_h / 2),
                size=(self.width, track_h),
                radius=[6]
            )
    
            # =====================
            # 2. ACTIVE RANGE
            # =====================
            x_min = self.x + (self.min_value / self.range_max) * self.width
            x_max = self.x + (self.max_value / self.range_max) * self.width
    
            Color(0, 1, 0, 0.75)
            RoundedRectangle(
                pos=(x_min, self.center_y - active_h / 2),
                size=(x_max - x_min, active_h),
                radius=[8]
            )
    
            # =====================
            # 3. HANDLES (DEUTLICH DICKER)
            # =====================
            Color(1, 1, 1, 1)
    
            Ellipse(
                pos=(x_min - handle_size / 2, self.center_y - handle_size / 2),
                size=(handle_size, handle_size)
            )
    
            Ellipse(
                pos=(x_max - handle_size / 2, self.center_y - handle_size / 2),
                size=(handle_size, handle_size)
            )

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._handle_touch(touch)
            return True

    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            self._handle_touch(touch)
            return True

    def _handle_touch(self, touch):
        # 1. Relative Position (0–1 clampen!)
        relative_x = (touch.x - self.x) / self.width
        relative_x = max(0.0, min(1.0, relative_x))
    
        # 2. Auf Range skalieren (0-100)
        raw_val = relative_x * (self.range_max - self.range_min) + self.range_min
        val = int(round(raw_val))
    
        # 3. HARD SNAP TO ZERO (Unsere mühsame Abschalt-Funktion)
        # Wenn der Finger ganz links (unter 3%) ist, schalten wir ALLES auf 0
        if relative_x < 0.03:
            self.min_value = 0
            self.max_value = 0
            return # Wichtig: Hier abbrechen, damit die Griff-Logik nicht überschreibt
    
        # 4. Normale Range-Begrenzung (Falls nicht 0, dann mindestens 1)
        val = max(1, min(self.range_max, val))
    
        # 5. Griff-Logik (Wer ist näher am Finger?)
        dist_min = abs(val - self.min_value)
        dist_max = abs(val - self.max_value)
    
        # Spezialfall: Wenn beide auf 0 stehen und wir ziehen nach rechts
        if self.max_value == 0:
            self.max_value = val
            return

        if dist_min < dist_max:
            # Linken Griff schieben, aber nicht über den rechten
            self.min_value = min(val, self.max_value)
        else:
            # Rechten Griff schieben, aber nicht unter den linken
            self.max_value = max(val, self.min_value)
class CirculationFanOverlay(FloatLayout):
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
            size=(dp_scaled(420), dp_scaled(420)),
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
            text="NATURAL FAN CONTROL", 
            bold=True, color=(0, 1, 0, 1),
            font_size=sp_scaled(16),
            halign="left"
        )
        
        self.sync_icon = Button(
            text="[font=FA]\uf021[/font]",
            markup=True,
            font_size=sp_scaled(26),
            size_hint=(None, None), 
            width=dp_scaled(45), height=dp_scaled(45),
            background_normal="", 
            background_down="", # Verhindert grauen Kasten beim Drücken
            background_color=(0, 0, 0, 0), # Hintergrund komplett UNSICHTBAR
            color=(1, 1, 1, 1) # Icon startet weiß
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

        # --- NEUER RANGE SLIDER ---
        self.panel.add_widget(Label(text="SPEED RANGE (MIN - MAX)", font_size=sp_scaled(11), color=(0,1,0,0.5), size_hint_y=None, height=dp_scaled(15)))
        
        self.range_slider = RangeSlider(size_hint_y=None, height=dp_scaled(40))
        # Wir binden die Werte-Änderung an deine bestehende Logik
        self.range_slider.bind(min_value=self._on_slider_change, max_value=self._on_slider_change)
        # Für das User-Active-Flag nutzen wir touch events
        self.range_slider.bind(on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        
        self.panel.add_widget(self.range_slider)

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
        
        # Nur die lokale Anzeige updaten (kein Netzwerk-Traffic!)
        min_v = int(self.range_slider.min_value)
        max_v = int(self.range_slider.max_value)
        self.lbl_val.text = f"{min_v}% - {max_v}%"
        
        # Icon auf Orange setzen (Benutzer ändert gerade etwas)
        self.sync_icon.text = "[font=FA]\uf021[/font]"
        self.sync_icon.color = (1, 0.5, 0, 1)
    
    def _force_sync(self, *_):
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac: return
        try:
            with open(self.sync_path, "r") as f:
                data = json.load(f).get(mac, {})
            payload = {
                "circulation_fan_pct": data.get("circulation_fan_pct", 0),
                "circulation_fan_min": data.get("circulation_fan_min", 0),
                "circulation_fan_mode": data.get("circulation_fan_mode", "man"),
                "rev": int(time.time())
            }
            WEB_CLIENT.send_control(mac, payload)
            self.sync_icon.color = (1, 1, 0, 1)
        except: pass

# --- ZUSÄTZLICHE OPTIMIERUNG DER UPDATE-LOGIK ---
    def update_ui(self, *_):
        # 1. Abbruch, falls noch nicht bereit oder User gerade schiebt
        if not getattr(WEB_CLIENT, "ready", False) or not self._init_done: 
            return
        
        now = time.time()
        if self._user_active or (now - self._last_user_action < 2.0):
            return
        
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac: return
    
        # 2. Daten vom Web-Client holen
        server_data = WEB_CLIENT.current_data.get(mac)
        if not server_data: return
    
        # Werte extrahieren
        srv_min = server_data.get('circulation_fan_min', 0)
        srv_max = server_data.get('circulation_fan_pct', 0) # 'pct' ist hier dein Max
        srv_mode = server_data.get('circulation_fan_mode', 'man')
        srv_rpm = server_data.get('circulation_fan_rpm', 0)
        server_rev = int(server_data.get('rev', 0))
    
        # --- 3. SYNC-CHECK (Das Herzstück für das grüne Icon) ---
        last_sent = getattr(self, '_last_sent_rev', 0)
        
        if server_rev < last_sent:
            # ESP/Server hat unseren neuen Stand noch nicht bestätigt
            self.sync_icon.text = "[font=FA]\uf021[/font]" # Sync-Icon
            self.sync_icon.color = (1, 0.5, 0, 1)        # Orange
            sync_pending = True
        else:
            # Synchronisation abgeschlossen!
            self.sync_icon.text = "[font=FA]\uf058[/font]" # Check-Icon
            self.sync_icon.color = (0, 1, 0, 1)           # GRÜN
            sync_pending = False
    
        # --- 4. UI AKTUALISIEREN ---
        self.lbl_val.text = f"{int(srv_min)}% - {int(srv_max)}%"
        self.lbl_rpm.text = f"RPM: {int(srv_rpm)}"
        
        # Slider nur nachziehen, wenn nicht gerade synchronisiert wird
        if not sync_pending:
            # Kleine Toleranz beim Vergleich (0.5)
            if abs(self.range_slider.min_value - srv_min) > 0.5:
                self.range_slider.min_value = srv_min
            if abs(self.range_slider.max_value - srv_max) > 0.5:
                self.range_slider.max_value = srv_max
            
            # Button Farben setzen
            self._apply_button_styles(srv_mode)

    def _apply_button_styles(self, mode):
        # Hilfsfunktion für konsistente Farben
        self.btn_man.background_color = (0, 1, 0, 0.6) if mode == "man" else (0.2, 0.2, 0.2, 1)
        self.btn_nat.background_color = (0, 0.7, 1, 0.6) if mode == "nat" else (0.2, 0.2, 0.2, 1)
        self.btn_chao.background_color = (1, 0.5, 0, 0.6) if mode == "chao" else (0.2, 0.2, 0.2, 1)
    def _send_current_range_to_server(self):
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac: return
        
        min_v = int(self.range_slider.min_value)
        max_v = int(self.range_slider.max_value)
        
        new_rev = int(time.time())
        self._last_sent_rev = new_rev
        
        print(f"[UI] Sende finalen Range-Wert: {min_v}-{max_v}%")
        WEB_CLIENT.send_control(mac, {
            "circulation_fan_pct": max_v,
            "circulation_fan_min": min_v,
            "rev": new_rev
        })
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
        self._last_sent_rev = new_rev 
        self._last_user_action = now  

        # UI Update
        self._set_mode_ui_only(mode)
        
        self.sync_icon.text = "[font=FA]\uf021[/font]"
        self.sync_icon.color = (1, 0.5, 0, 1)

        # KORREKTUR HIER: Zugriff auf die richtigen Properties des RangeSliders
        payload = {
            "circulation_fan_pct": int(self.range_slider.max_value), # Nicht .max.value
            "circulation_fan_min": int(self.range_slider.min_value), # Nicht .min.value
            "circulation_fan_mode": mode,
            "rev": new_rev
        }
        WEB_CLIENT.send_control(mac, payload)
        
        self._pending_updates.update({"circulation_fan_mode": mode, "rev": new_rev})
        self._sync_to_client(0)
    def _touch_down(self, instance, touch):
        if instance.collide_point(*touch.pos):
            self._user_active = True
            # Optional: Timer stoppen, damit nichts flackert
            return False # Kivy-Standard: Event weiterreichen

    def _touch_up(self, instance, touch):
        if self._user_active:
            self._user_active = False
            self._last_user_action = time.time()
            
            # WICHTIG: Erst jetzt schicken wir den endgültigen Wert an den Server!
            self._send_current_range_to_server()
            return False
    def _u(self, *_):
        self.bg_rect.pos = self.panel.pos
        self.bg_rect.size = self.panel.size
        self.outline.rounded_rectangle = (self.panel.x, self.panel.y, self.panel.width, self.panel.height, dp_scaled(20))

    def close(self):
        if self._update_event: self._update_event.cancel()
        if self._sync_event: self._sync_event.cancel()
        if self.parent: self.parent.remove_widget(self)
        GLOBAL_STATE.ui_handler.active_circulation_fan_overlay = None

    def _init_values(self, *_):
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac: return
    
        # 1. Wir holen uns den AKTUELLEN Stand vom WEB_CLIENT Speicher (nicht nur File)
        server_data = WEB_CLIENT.current_data.get(mac, {})
        
        # Wenn der Server Daten hat, nehmen wir die als Basis für unsere UI
        if server_data:
            saved_min = server_data.get("circulation_fan_min", 20)
            saved_max = server_data.get("circulation_fan_pct", 60)
            saved_mode = server_data.get("circulation_fan_mode", "nat")
        else:
            # Nur wenn gar nichts da ist, aus Datei oder Default
            saved_min = 20
            saved_max = 60
            saved_mode = "nat"
    
        self.range_slider.min_value = saved_min
        self.range_slider.max_value = saved_max
        self._set_mode_ui_only(saved_mode) # Neue Hilfsfunktion für Farben
    
        self._init_done = True
        # Der erste Sync erfolgt jetzt erst, wenn der User wirklich was drückt 
        # ODER wenn update_ui das erste Mal die Revisionen glattzieht.

    def _set_mode_ui_only(self, mode):
        self.btn_man.background_color = (0, 1, 0, 0.6) if mode == "man" else (0.2, 0.2, 0.2, 1)
        self.btn_nat.background_color = (0, 0.7, 1, 0.6) if mode == "nat" else (0.2, 0.2, 0.2, 1)
        self.btn_chao.background_color = (1, 0.2, 0.2, 0.6) if mode == "chao" else (0.2, 0.2, 0.2, 1)