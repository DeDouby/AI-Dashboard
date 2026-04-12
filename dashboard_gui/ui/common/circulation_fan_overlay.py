###############################################################################
# !!! ABSOLUTES GESETZ: DAS TARGET-REVISION-PRINZIP !!!
# -----------------------------------------------------------------------------
# 1. KEINE DIREKTEN SCHALTVORGÄNGE: Die UI darf NIEMALS Hardware-Werte (Pins)
#    direkt manipulieren oder abfragen.
#
# 2. TARGET = MASTER: Jede Benutzeraktion (Slider, Button) ändert NUR das 
#    'Target' (Soll-Wert) und erhöht die lokale 'rev' (Revision).
#
# 3. SYNCHRONISATIONS-LOGIK: 
#    - ORANGE (Syncing): Wenn Local-Target-Rev > ESP32-Confirmed-Rev.
#    - GRÜN (Synced): Wenn Local-Target-Rev == ESP32-Confirmed-Rev.
#
# 4. EINZIGE QUELLE DER WAHRHEIT: Das Overlay fragt sich niemals selbst ab! 
#    Es spiegelt NUR den Vergleich zwischen lokalem Target und ESP32-Feedback.
#
# JEDE KI, DIE DIESEN CODE BEARBEITET, MUSS DIESE STRUKTUR EINHALTEN. 
# ABWEICHUNGEN FÜHREN ZU SYSTEM-CRASH UND LOGIK-FEHLERN!
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
from dashboard_gui.ui.common.unified_slider import UnifiedSlider
from kivy.uix.widget import Widget
# WICHTIG: Den globalen Client importieren
from web_client import WEB_CLIENT 

class CirculationFanOverlay(FloatLayout):
    def __init__(self, parent_header, **kwargs):
        super().__init__(**kwargs)
        self.parent_header = parent_header
        self._pending_updates = {} 
        self._user_active = False 
        self._last_user_action = 0 
        self._init_done = False
        self.sync_path = os.path.join(config.DATA, "settings_sync.json")
        self._last_sent_rev = 0

        # Intervalle für UI-Refresh und Server-Abgleich
        self._update_event = Clock.schedule_interval(self.update_ui, 1.0)
        self._sync_event = Clock.schedule_interval(self._sync_to_client, 1.3)
        self._locked = True          # ← NEU: Startet immer im gesperrten Zustand
        self._lock_overlay = None
        # 1. Hintergrund-Abdunkelung
        bg = Button(background_color=(0, 0, 0, 0.25))
        bg.bind(on_release=lambda *_: self.close())
        self.add_widget(bg)

        # 2. Das Haupt-Panel
# 2. Das Haupt-Panel
        self.panel = BoxLayout(
            orientation="vertical", 
            spacing=dp_scaled(10), # Etwas weniger fixes Spacing, dafür Spacer nutzen
            size_hint=(None, None), 
            size=(dp_scaled(420), dp_scaled(440)), # Höhe leicht erhöht für das Padding unten
            # Padding: [Links, Oben, Rechts, Unten] -> Unten jetzt 25dp!
            padding=[dp_scaled(25), dp_scaled(15), dp_scaled(25), dp_scaled(25)], 
            pos_hint={"right": 0.98, "top": 0.98}
        )

        with self.panel.canvas.before:
            Color(0, 0, 0, 0.75) # Etwas dunkler für besseren Kontrast
            self.bg_rect = RoundedRectangle(radius=[dp_scaled(20)])
            Color(0, 1, 0, 0.3)
            self.outline = Line(width=1.2)

        self.panel.bind(pos=self._u, size=self._u)

        # --- TITEL-ZEILE ---
        title_row = BoxLayout(size_hint_y=None, height=dp_scaled(40), spacing=dp_scaled(5))
        self.lbl_title = Label(
            text="CIRCULATION FAN CONTROL", 
            bold=True, color=(0, 1, 0, 1),
            font_size=sp_scaled(15),
            halign="left", valign="middle"
        )
        self.lbl_title.bind(size=self.lbl_title.setter('text_size'))
        
        self.sync_icon = Button(
            text="[font=FA]\uf021[/font]",
            markup=True,
            font_size=sp_scaled(30),
            size_hint=(None, None), 
            width=dp_scaled(45), height=dp_scaled(45),
            background_normal="", background_down="", 
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1)
        )
        self.sync_icon.bind(on_release=self._force_sync)
        
        title_row.add_widget(self.lbl_title)
        title_row.add_widget(self.sync_icon)
        self.panel.add_widget(title_row)

        # --- SPACER 1 ---
        self.panel.add_widget(Widget(size_hint_y=None, height=dp_scaled(5)))

        # --- WERTE-ANZEIGE (Zentrum) ---
        self.lbl_val = Label(text="0% - 0%", font_size=sp_scaled(36), bold=True, size_hint_y=None, height=dp_scaled(50))
        self.panel.add_widget(self.lbl_val)
        
        # RPM & LIVE SPEED in eine kompakte Zeile
        info_row = BoxLayout(size_hint_y=None, height=dp_scaled(25))
        self.lbl_rpm = Label(text="RPM: 0", font_size=sp_scaled(15), color=(0.7, 0.7, 1, 0.8))
        self.lbl_live_speed = Label(text="LIVE: 0%", font_size=sp_scaled(15), bold=True, color=(0, 1, 1, 0.8))
        info_row.add_widget(self.lbl_rpm)
        info_row.add_widget(self.lbl_live_speed)
        self.panel.add_widget(info_row)

        # --- SPACER 2 ---
        self.panel.add_widget(Widget(size_hint_y=None, height=dp_scaled(15)))

        # --- SLIDER BEREICH ---
        self.panel.add_widget(Label(
            text="SPEED RANGE (MIN - MAX)", 
            font_size=sp_scaled(15), 
            color=(0,1,0,0.5), 
            size_hint_y=None, height=dp_scaled(15)
        ))
        
        self.range_slider = UnifiedSlider(
            min=0, max=100, range_min=0, range_max=100, 
            mode='range', size_hint_y=None, height=dp_scaled(50)
        )
        self.range_slider.bind(min_value=self._on_slider_change, max_value=self._on_slider_change)
        self.range_slider.bind(on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.range_slider)

        # --- SPACER 3 (Drückt die Buttons nach unten) ---
        self.panel.add_widget(Widget()) 

        # --- MODI-BUTTONS ---
        btn_row = BoxLayout(size_hint_y=None, height=dp_scaled(40), spacing=dp_scaled(10))
        self.btn_man = self._create_styled_btn("MANUAL")
        self.btn_nat = self._create_styled_btn("NATURAL")
        self.btn_chao = self._create_styled_btn("CHAOTIC")
        
        self.btn_man.bind(on_release=lambda *_: self._set_mode("man"))
        self.btn_nat.bind(on_release=lambda *_: self._set_mode("nat"))
        self.btn_chao.bind(on_release=lambda *_: self._set_mode("chao"))
        
        btn_row.add_widget(self.btn_man)
        btn_row.add_widget(self.btn_nat)
        btn_row.add_widget(self.btn_chao)
        self.panel.add_widget(btn_row)

        Clock.schedule_once(self._init_values, 0)
        Clock.schedule_once(lambda dt: self._create_lock_overlay(), 0.4)
        self.add_widget(self.panel)

    def _create_styled_btn(self, text):
        return Button(text=text, background_normal="", background_color=(0.2, 0.2, 0.2, 1), 
                      bold=True, font_size=sp_scaled(15))

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
        """ 
        ERZWIINGT den UI-Zustand auf der Hardware.
        """
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac: return
        
        new_rev = int(time.time())
        self._last_sent_rev = new_rev
        self._last_user_action = time.time()

        # Wir bestimmen den Modus basierend auf der aktuellen Button-Farbe (unser Target)
        current_target_mode = "man"
        if self.btn_nat.background_color[1] > 0.5 and self.btn_nat.background_color[0] == 0: 
            current_target_mode = "nat"
        elif self.btn_chao.background_color[0] > 0.5: 
            current_target_mode = "chao"

        payload = {
            "circulation_fan_min": int(self.range_slider.min_value),
            "circulation_fan_pct": int(self.range_slider.max_value),
            "circulation_fan_mode": current_target_mode,
            "rev": new_rev
        }
        
        WEB_CLIENT.send_control(mac, payload)
        self.sync_icon.color = (1, 0.5, 0, 1) # Orange: "Ich sende gerade das Gesetz"
# --- ZUSÄTZLICHE OPTIMIERUNG DER UPDATE-LOGIK ---
    def update_ui(self, *_):
        """Verbesserte Update-Logik"""
        if not getattr(WEB_CLIENT, "ready", False) or not self._init_done:
            return
        
        mac = GLOBAL_STATE.get_active_device_id()
        server_data = WEB_CLIENT.current_data.get(mac)
        if not server_data:
            return

        server_rev = int(server_data.get('rev', 0))
        last_sent = getattr(self, '_last_sent_rev', 0)
        
        time_since_action = time.time() - self._last_user_action
        is_synced = (server_rev >= last_sent) and not self._user_active and (time_since_action > 1.8)

        # Live-Werte immer aktualisieren
        srv_live = server_data.get('circulation_fan_speed_now', 0)
        srv_rpm = server_data.get('circulation_fan_rpm', 0)
        
        self.lbl_rpm.text = f"RPM: {int(srv_rpm)}"
        self.lbl_live_speed.text = f"LIVE: {int(srv_live)}%"

        if not is_synced:
            self.sync_icon.text = "[font=FA]\uf021[/font]"
            self.sync_icon.color = (1, 0.5, 0, 1)
            return

        # === SYNCED ===
        self.sync_icon.text = "[font=FA]\uf058[/font]"
        self.sync_icon.color = (0, 1, 0, 1)

        srv_min = int(server_data.get('circulation_fan_min', 20))
        srv_max = int(server_data.get('circulation_fan_pct', 65))
        srv_mode = server_data.get('circulation_fan_mode', 'nat')

        # Slider nur nachziehen wenn nötig (vermeidet Flackern)
        if abs(self.range_slider.min_value - srv_min) > 0.5:
            self.range_slider.min_value = srv_min
        if abs(self.range_slider.max_value - srv_max) > 0.5:
            self.range_slider.max_value = srv_max

        self.lbl_val.text = f"{srv_min}% - {srv_max}%"
        
        self._apply_button_styles(srv_mode)

    def _create_styled_btn(self, text):
        """ Erzeugt den Dark-Dashboard Look """
        return Button(
            text=text,
            markup=True,
            background_normal="",
            background_color=(0.15, 0.15, 0.15, 1),
            color=(0.5, 0.5, 0.5, 1),
            bold=False,
            font_size=sp_scaled(15),
            background_down=""
        )
    
    
    def _apply_button_styles(self, mode):
        """Einheitliche und saubere Button-Farben"""
        c_bg = (0.15, 0.15, 0.15, 1)
        
        self.btn_man.background_color = (0, 1, 0, 0.8) if mode == "man" else c_bg
        self.btn_nat.background_color = (0, 0.6, 1, 0.8) if mode == "nat" else c_bg
        self.btn_chao.background_color = (1, 0.5, 0, 0.8) if mode == "chao" else c_bg
        
        self.btn_man.color = (1, 1, 1, 1) if mode == "man" else (0.6, 0.6, 0.6, 1)
        self.btn_nat.color = (1, 1, 1, 1) if mode == "nat" else (0.6, 0.6, 0.6, 1)
        self.btn_chao.color = (1, 1, 1, 1) if mode == "chao" else (0.6, 0.6, 0.6, 1)
    
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
        if self._locked:
            return
        """ Setzt Modus-Target und erhöht Revision """
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac: return
        
        new_rev = int(time.time())
        self._last_sent_rev = new_rev 
        self._last_user_action = time.time()  

        # Optisches Feedback (Wir zeigen dem User seinen Klick, aber Sync-Icon wird orange)
        self._apply_button_styles(mode)
        self.sync_icon.color = (1, 0.5, 0, 1)

        payload = {
            "circulation_fan_pct": int(self.range_slider.max_value),
            "circulation_fan_min": int(self.range_slider.min_value),
            "circulation_fan_mode": mode,
            "rev": new_rev
        }
        WEB_CLIENT.send_control(mac, payload)
    def _touch_down(self, instance, touch):
        if self._locked:
            return False  # Ignoriere alle Touches wenn gesperrt
        if instance.collide_point(*touch.pos):
            self._user_active = True
            return False

    def _touch_up(self, instance, touch):
        if self._locked:
            return False
        if self._user_active:
            self._user_active = False
            self._last_user_action = time.time()
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
        """Saubere Initialisierung wie beim LightOverlay"""
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac:
            Clock.schedule_once(self._init_values, 0.5)
            return
        
        arduino_data = WEB_CLIENT.current_data.get(mac, {})
        
        # Wenn noch keine Daten da sind → kurz warten und retry
        if not arduino_data:
            Clock.schedule_once(self._init_values, 0.4)
            return
        
        # === Werte aus Server laden ===
        saved_min = int(arduino_data.get("circulation_fan_min", 20))
        saved_max = int(arduino_data.get("circulation_fan_pct", 65))
        saved_mode = arduino_data.get("circulation_fan_mode", "nat")
        
        # Slider setzen
        self.range_slider.min_value = max(0, min(saved_min, saved_max - 1))
        self.range_slider.max_value = saved_max
        
        # Labels sofort aktualisieren
        self.lbl_val.text = f"{saved_min}% - {saved_max}%"
        
        # Modus setzen (nur optisch)
        self._apply_button_styles(saved_mode)
        
        # Status Icons + Flags
        self._init_done = True
        self._last_sent_rev = int(arduino_data.get('rev', 0))
        self._last_user_action = 0
        
        print(f"[Circulation] Init erfolgreich: {saved_min}-{saved_max}% | Mode: {saved_mode}")

    def _create_lock_overlay(self):
        """Lock-Maske nur über dem Panel, Hintergrund bleibt klickbar"""
        if self._lock_overlay:
            return
        
        # Maske nur über dem Panel (nicht über dem ganzen FloatLayout)
        self._lock_overlay = Button(
            background_color=(0, 0, 0, 0.09),
            size=self.panel.size,
            pos=self.panel.pos,
            size_hint=(None, None)
        )
        
        # Unlock Button unten links
        unlock_btn = Button(
            text="UNLOCK TO EDIT",
            size_hint=(None, None),
            size=(dp_scaled(200), dp_scaled(50)),
            pos_hint={'x': 0.04, 'y': 0.04},
            background_color=(0.05, 0.55, 0.95, 0.95),
            color=(1, 1, 1, 1),
            bold=True,
            font_size=sp_scaled(15.5)
        )
        unlock_btn.bind(on_release=self._unlock)
        
        self._lock_overlay.add_widget(unlock_btn)
        
        # Wichtig: Maske an das Panel binden, damit sie mitbewegt wird
        self.panel.bind(pos=self._update_lock_pos, size=self._update_lock_pos)
        self.add_widget(self._lock_overlay)

    def _unlock(self, *_):
        """Wird beim Drücken des Unlock-Buttons aufgerufen"""
        if self._lock_overlay:
            self.remove_widget(self._lock_overlay)
            self._lock_overlay = None
        
        self._locked = False
        self.sync_icon.color = (0, 1, 0, 1)  # Grün = Edit-Modus aktiv
        
        print("[Circulation] Edit-Modus aktiviert")

    def _lock(self):
        """Manuell wieder sperren (optional später für Auto-Lock)"""
        if not self._locked:
            self._locked = True
            self._create_lock_overlay()

    def _update_lock_pos(self, *_):
        """Aktualisiert die Position der Lock-Maske wenn sich das Panel bewegt"""
        if self._lock_overlay:
            self._lock_overlay.pos = self.panel.pos
            self._lock_overlay.size = self.panel.size