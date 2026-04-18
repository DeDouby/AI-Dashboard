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
from dashboard_gui.overlays.unified_slider import UnifiedSlider
from dashboard_gui.overlays.lock_overlay import LockOverlay
from kivy.uix.widget import Widget
# WICHTIG: Den globalen Client importieren

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
        self._locked = True
        self._target_mode = "nat"  # Target-State: Standard "natural"
        self._last_user_action = time.time()  # Startwert
        # 1. Hintergrund-Abdunkelung
        bg = Button(background_color=(0, 0, 0, 0.25))
        bg.bind(on_release=lambda *_: self.close())
        self.add_widget(bg)
        self._ui_lock = False
        self._target_state = {
            "min": 20,
            "max": 65,
            "mode": "nat"
        }
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
            min=0, 
            max=100, 
            mode='range', 
            # range_min und range_max WEG LASSEN!
            # fill_entire_track=True kannst du bei Bedarf hinzufügen, falls es optisch passt
            size_hint_y=None, 
            height=dp_scaled(50)
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
        
        # Lock-Overlay initialisieren
        self.lock_overlay = LockOverlay(
            parent=self,
            panel=self.panel,
            unlock_callback=self._on_unlock
        )
        Clock.schedule_once(lambda dt: self.lock_overlay.create(), 0.4)
        
        self.add_widget(self.panel)



    def _on_slider_change(self, instance, value):
        if not self._init_done or self._ui_lock: 
            return
        if not self._init_done: return
        if getattr(self, "_ui_lock", False):
            return
        # Nur die lokale Anzeige updaten (kein Netzwerk-Traffic!)
        min_v = int(self.range_slider.min_value)
        max_v = int(self.range_slider.max_value)
        self.lbl_val.text = f"{min_v}% - {max_v}%"
        self._target_state["min"] = int(self.range_slider.min_value)
        self._target_state["max"] = int(self.range_slider.max_value)
        # Icon auf Orange setzen (Benutzer ändert gerade etwas)
        self._set_orange()
    
    # In deinem Overlay
    def _force_sync(self, *_):
        new_rev = GLOBAL_STATE.send_overlay_command(
            "circulation_fan",
            min=int(self.range_slider.min_value),
            max=int(self.range_slider.max_value),
            mode=self._target_state["mode"]
        )
    
        if new_rev:
            self._last_sent_rev = new_rev
            self._last_user_action = time.time()
            self.sync_icon.color = (1, 0.5, 0, 1)
    
    def _set_orange(self):
        """Orange Sync-Status (Änderung läuft / nicht bestätigt)"""
        self.sync_icon.text = "[font=FA]\uf021[/font]"
        self.sync_icon.color = (1, 0.5, 0, 1)

    def _set_green(self):
        """Grüner Sync-Status (alles bestätigt)"""
        self.sync_icon.text = "[font=FA]\uf058[/font]"
        self.sync_icon.color = (0, 1, 0, 1)    
    
    def update_ui(self, *_):
        mac = GLOBAL_STATE.get_active_device_id()
        server_data = GLOBAL_STATE.overlay_engine.get_buffer_data(mac)
        if not server_data: return

        # SESSION-CHECK
        current_init_rev = server_data.get('rev_init_circfan', 0)
        if not hasattr(self, "_last_adopted_init") or self._last_adopted_init != current_init_rev:
            self._last_adopted_init = current_init_rev
            return

        server_rev = int(server_data.get('rev_circfan', 0))
        last_sent = getattr(self, '_last_sent_rev', 0)
        
        # LOGIK: Wir ignorieren Server-Werte für die Slider-Position, 
        # solange unsere lokale Revision (last_sent) höher ist als das, 
        # was der ESP32 bisher bestätigt hat (server_rev).
        time_since_action = time.time() - self._last_user_action
        
        # Ein Sync ist NUR erfolgt, wenn der Server unsere Rev bestätigt hat 
        # UND der User nicht gerade schiebt UND die Beruhigungszeit um ist.
        is_synced = (server_rev >= last_sent) and not self._user_active and (time_since_action > 1.5)

        # Live-Werte (immer anzeigen, da Hardware-Feedback)
        srv_live = server_data.get('circulation_fan_speed_now', 0)
        srv_rpm = server_data.get('circulation_fan_rpm', 0)
        self.lbl_rpm.text = f"RPM: {int(srv_rpm)}"
        self.lbl_live_speed.text = f"LIVE: {int(srv_live)}%"

        if not is_synced:
            # STATUS ORANGE: Wir zeigen unsere LOKALEN Target-Werte. 
            # Der Slider bleibt, wo der User ihn hingeschoben hat.
            self.sync_icon.text = "[font=FA]\uf021[/font]"
            self.sync_icon.color = (1, 0.5, 0, 1)
            # WICHTIG: Kein Setzen von self.range_slider hier!
            return

        # === STATUS GRÜN (SYNCED) ===
        self.sync_icon.text = "[font=FA]\uf058[/font]"
        self.sync_icon.color = (0, 1, 0, 1)

        srv_min = int(server_data.get('circulation_fan_min', 20))
        srv_max = int(server_data.get('circulation_fan_pct', 65))
        srv_mode = server_data.get('circulation_fan_mode', 'nat')

        # Nur im Synced-Zustand gleichen wir die Slider-Hardware-Positionen an,
        # falls sie (z.B. durch andere Clients) abweichen.
        if not self._user_active:
            # Wir nutzen _ui_lock, damit das Setzen der Werte keinen neuen Command auslöst!
            self._ui_lock = True 
            if abs(self.range_slider.max_value - srv_max) > 0.5:
                self.range_slider.max_value = srv_max
            if abs(self.range_slider.min_value - srv_min) > 0.5:
                self.range_slider.min_value = srv_min
            self._ui_lock = False

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
        self._last_sent_rev = GLOBAL_STATE.send_overlay_command(
            "circulation_fan_range",
            min=int(self.range_slider.min_value),
            max=int(self.range_slider.max_value),
            mode=self._target_state["mode"]
        
        )
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
        
        # 1. Ziel-Modus lokal im Overlay merken
        self._target_state["mode"] = mode
        
        # 2. Befehl über den GSM abfeuern
        # Wir nutzen dein 'send_overlay_command' Schema
        new_rev = GLOBAL_STATE.send_overlay_command(
            "circulation_fan",
            min=self.range_slider.min_value,
            max=self.range_slider.max_value,
            mode=mode
        )

        # 3. Visuelles Feedback (Orange) und Zeitstempel für Sync-Logik
        if new_rev:
            self._last_sent_rev = new_rev 
            self._last_user_action = time.time()
            self._set_orange()

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
        widget = self.parent_header
        # Wir holen uns die Daten direkt über den neuen sauberen Weg
        mac = GLOBAL_STATE.get_active_device_id()
        data = GLOBAL_STATE.overlay_engine.get_buffer_data(mac)

        if not data:
            Clock.schedule_once(self._init_values, 0.3)
            return

        # 1. Werte extrahieren
        srv_min = data.get("circulation_fan_min", 20)
        srv_max = data.get("circulation_fan_pct", 65)
        srv_mode = data.get("circulation_fan_mode", "nat")

        # 2. SLIDER SETZEN (Wichtig: Erst Werte, dann Init-Flag)
        self._ui_lock = True

        self.range_slider.max_value = srv_max
        self.range_slider.min_value = srv_min

        self._ui_lock = False
        self._target_mode = srv_mode
        
        # 3. FIX: Label explizit updaten (Das hat gefehlt!)
        self.lbl_val.text = f"{int(srv_min)}% - {int(srv_max)}%"
        
        # 4. Button-Styles anwenden (Wie im Light-Modul)
        self._apply_button_styles(srv_mode)

        # 5. Abschluss
        self._pending_updates.clear()
        self._init_done = True  # Jetzt erst darf der Slider-Bind Traffic machen
        self.range_slider.disabled = False
    
    def _on_unlock(self):
        """Callback wenn Lock aufgegeben wird."""
        self._locked = False
        self._set_sliders_disabled(False)

    def _set_sliders_disabled(self, state):
        """Schaltet den Slider ein/aus."""
        if hasattr(self, 'range_slider'):
            self.range_slider.disabled = state

