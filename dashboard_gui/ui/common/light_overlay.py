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
from kivy.uix.scrollview import ScrollView
import config 
import time 
import json 
import os
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.ui.common.unified_slider import UnifiedSlider

# WICHTIG: Den globalen Client importieren
from web_client import WEB_CLIENT 

class LightOverlay(FloatLayout):
    def __init__(self, parent_header, **kwargs):
        super().__init__(**kwargs)
        self.parent_header = parent_header
        self._pending_updates = {} 
        self._user_active = False 
        self._last_user_action = 0 
        self._init_done = False
        # Intervalle für UI-Refresh und Server-Abgleich
        self._update_event = Clock.schedule_interval(self.update_ui, 1.0)
        self._sync_event = Clock.schedule_interval(self._sync_to_client, 1.3)
        self._intended_mode = "man"
        # 1. Hintergrund-Abdunkelung
        bg = Button(background_color=(0, 0, 0, 0.25))
        bg.bind(on_release=lambda *_: self.close())
        self.add_widget(bg)

        # 2. Das Haupt-Panel
        self.panel = BoxLayout(
            orientation="vertical", 
            padding=dp_scaled(20), 
            spacing=dp_scaled(15),
            size_hint=(None, None), 
            size=(dp_scaled(420), dp_scaled(500)),  # etwas höher für mobile
            pos_hint={"right": 0.98, "top": 0.98}
        )

        with self.panel.canvas.before:
            Color(0, 0, 0, 0.65)
            self.bg_rect = RoundedRectangle(radius=[dp_scaled(20)])
            Color(0, 1, 0, 0.4)
            self.outline = Line(width=1.2)

        self.panel.bind(pos=self._u, size=self._u)



        # --- TITEL-ZEILE MIT SYNC-HAKEN ---
        title_row = BoxLayout(size_hint_y=None, height=dp_scaled(30), spacing=dp_scaled(5))
        
        self.lbl_title = Label(
            text="LIGHT CONTROL PRO", 
            bold=True, color=(0, 1, 0, 1),
            font_size=sp_scaled(16),
            halign="left"
        )
        
        # DAS ICON (Nutzt Font Awesome)
        # DAS ICON (Initialzustand)
        self.sync_icon = Button(
            text="[font=FA]\uf021[/font]",
            markup=True,
        
            font_size=sp_scaled(26),
        
            size_hint_x=None,
            width=dp_scaled(40),
            size_hint_y=None,
            height=dp_scaled(40),
        
            background_normal="",
            background_color=(0, 0, 0, 0)
        )
        
        self.sync_icon.bind(on_release=self._force_sync)
        
        title_row.add_widget(self.lbl_title)
        title_row.add_widget(self.sync_icon)
        self.scroll = ScrollView(
            size_hint=(1, 1),
            do_scroll_x=False,
            do_scroll_y=True
        )
        
        self.content = BoxLayout(
            orientation="vertical",
            spacing=dp_scaled(15),
            padding=[dp_scaled(20), 0, dp_scaled(20), 0], # LINKS und RECHTS Padding hinzufügen
            size_hint_y=None
        )
        
        self.content.bind(minimum_height=self.content.setter('height'))
        
        self.scroll.add_widget(self.content)
        self.content.add_widget(title_row)
        self.panel.add_widget(self.scroll)
        
        
        # --- WERTE-ANZEIGE ---
        self.lbl_val = Label(text="SYNC...", font_size=sp_scaled(45), bold=True, color=(1, 0.5, 0, 1))
        self.content.add_widget(self.lbl_val)
        # In der __init__ nach self.lbl_val hinzufügen:
        self.lbl_status_text = Label(
            text="TIMER: SCHLÄFT", 
            font_size=sp_scaled(14), 
            bold=True,
            color=(0.5, 0.5, 0.5, 1) # Grau wenn aus
        )
        self.content.add_widget(self.lbl_status_text)
        # Main brightness slider - now UnifiedSlider in single-mode
        # Functionally identical to Slider but supports future 2-point expansion
        self.slider = UnifiedSlider(
            min=0, max=100, range_min=0, range_max=100, 
            mode='single',
            size_hint_y=None, height=dp_scaled(45)
        )
        self.slider.bind(value=self._on_slider_change, on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.content.add_widget(self.slider)

 
        
        
        # Restzeit Anzeige
        self.lbl_remaining = Label(
            text="", 
            font_size=sp_scaled(14), 
            color=(1, 0.8, 0, 1), # Goldgelb wie im Browser
            size_hint_y=None, 
            height=dp_scaled(20)
        )
        self.content.add_widget(self.lbl_remaining)
        
        # --- MODI-BUTTONS (Erweitert um TIMER) ---
        btn_row = BoxLayout(size_hint_y=None, height=dp_scaled(45), spacing=dp_scaled(8))
        self.btn_man = self._create_styled_btn("MANUELL")
        self.btn_tim = self._create_styled_btn("TIMER")
        # BREATH IST RAUS -> Wir könnten hier einen "OFF" oder "SYNC" Button lassen
        self.btn_off = self._create_styled_btn("AUS") 
        
        self.btn_man.bind(on_release=lambda *_: self._set_mode("man"))
        self.btn_tim.bind(on_release=lambda *_: self._set_mode("tim"))
        self.btn_off.bind(on_release=lambda *_: self._set_mode("off")) # Schaltet Licht auf 0% & Manuell
        
        btn_row.add_widget(self.btn_man)
        btn_row.add_widget(self.btn_tim)
        btn_row.add_widget(self.btn_off)
        self.content.add_widget(btn_row)

        # --- SUNRISE/SUNSET RAMPEN (2-Punkt Slider) ---
        self.sunrise_sunset_box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp_scaled(90), spacing=dp_scaled(5))
        
        self.lbl_sunrise_sunset = Label(
            text="[font=FA]\uf185[/font] SUNRISE: 1h ↑ / [font=FA]\uf186[/font] SUNSET: 1h ↓", 
            font_size=sp_scaled(14),
            color=(1, 0.8, 0.2, 1),
            markup=True
        )
        
        # 2-Punkt Slider: min=Sunrise-Minuten im Timer, max=Sunset-Minuten im Timer
        self.slider_sunrise_sunset = UnifiedSlider(
            min=1, max=96, range_min=1, range_max=96,  # Steps (1 Step = 15min)
            mode='range',
            fill_entire_track=True,  # Exklusiv für diesen Slider: voller Track grün
            size_hint_y=None, height=dp_scaled(45)
        )
        self.slider_sunrise_sunset.bind(
            min_value=self._on_sunrise_sunset_change,
            max_value=self._on_sunrise_sunset_change,
            on_touch_down=self._touch_down,
            on_touch_up=self._touch_up
        )
        
        self.sunrise_sunset_box.add_widget(self.lbl_sunrise_sunset)
        self.sunrise_sunset_box.add_widget(self.slider_sunrise_sunset)
        self.content.add_widget(self.sunrise_sunset_box)

        # --- TIMER-EINSTELLUNG (NEU: Wie im Browser) ---
        # --- TIMER-EINSTELLUNG (FLEXIBEL) ---
        self.timer_box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp_scaled(120), spacing=dp_scaled(5))
        
        # STARTZEIT (15 MIN RASTER)
        self.lbl_start = Label(text="START: 08:00", font_size=sp_scaled(14))
        
        self.slider_start = UnifiedSlider(
            min=0, max=95, range_min=0, range_max=95,
            mode='single',
            size_hint_y=None, height=dp_scaled(45)
        )
        self.slider_start.value = 32
        self.slider_start.bind(
            value=self._on_start_change,
            on_touch_down=self._touch_down,
            on_touch_up=self._touch_up
        )        
        # DAUER (15-min Raster: 15min bis 24h = 15 bis 1440 Minuten)
        self.lbl_dur = Label(text="DAUER: 720 min", font_size=sp_scaled(14))
        
        self.slider_dur = UnifiedSlider(
            min=1, max=96, range_min=1, range_max=96,  # 1 = 15min, 96 = 24h
            mode='single',
            size_hint_y=None, height=dp_scaled(45)
        )
        self.slider_dur.value = 48  # 48 * 15min = 720min = 12h
        self.slider_dur.bind(
            value=self._on_dur_change,
            on_touch_down=self._touch_down,
            on_touch_up=self._touch_up
        )        
        self.timer_box.add_widget(self.lbl_start)
        self.timer_box.add_widget(self.slider_start)
        self.timer_box.add_widget(self.lbl_dur)
        self.timer_box.add_widget(self.slider_dur)
        
        self.content.add_widget(self.timer_box)

        
        Clock.schedule_once(self._init_values, 0)
        self.add_widget(self.panel)

    def _create_styled_btn(self, text):
        return Button(text=text, background_normal="", background_color=(0.2, 0.2, 0.2, 1), 
                      bold=True, font_size=sp_scaled(10))



    def _force_sync(self, *_):
        """
        GEWALT-MODUS: Erhebt den aktuellen UI-Zustand zum Gesetz.
        Erhöht die Revision massiv, damit der ESP32 alle internen 
        Zustände mit den UI-Werten überschreibt.
        """
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac: return
    
        # Wir erzeugen eine neue Zeitstempel-Revision
        new_rev = int(time.time())
        self._last_sent_rev = new_rev
        self._last_user_action = time.time() # Sperrt UI-Overwrite für 2 Sek

        # Wir lesen die WÜNSCHE der UI aus (Targets)
        try:
            start_step = int(self.slider_start.value)
            h, m = (start_step * 15) // 60, (start_step * 15) % 60
            
            current_intended_mode = "tim" if self.btn_tim.background_color[1] > 0.5 else "man"
            
            # Dauer in Minuten
            dur_steps = int(self.slider_dur.value)
            dur_min = dur_steps * 15
            
            # Sunrise/Sunset: min_value = Anfang, max_value = vom Ende
            sr_steps = int(self.slider_sunrise_sunset.min_value)
            ss_steps = int(self.slider_sunrise_sunset.range_max - self.slider_sunrise_sunset.max_value)
            sr_min = sr_steps * 15
            ss_min = ss_steps * 15

            payload = {
                "light_pct": int(self.slider.value),
                "light_mode": current_intended_mode,
                "l_start_h": h,
                "l_start_m": m,
                "l_dur": dur_min,
                "l_sunrise": sr_min,
                "l_sunset": ss_min,
                "rev": new_rev
            }
    
            WEB_CLIENT.send_control(mac, payload)
            
            self.sync_icon.text = "[font=FA]\uf021[/font]"
            self.sync_icon.color = (1, 0.5, 0, 1) 
        except Exception as e:
            print(f"Force Sync Error: {e}")

    def _set_mode(self, mode):
        """
        Ändert nur den WUNSCH-Modus.
        Die UI-Farbe ändert sich erst in update_ui(), wenn der ESP32 
        die Revision bestätigt hat.
        """
        # Lokale Revision erhöhen
        new_rev = int(time.time())
        self._last_sent_rev = new_rev
        self._last_user_action = time.time()
        self._intended_mode = "man"
        # Wir senden den Modus-Wunsch sofort ab
        mac = GLOBAL_STATE.get_active_device_id()
        if mac:
            payload = {"light_mode": mode, "rev": new_rev}
            WEB_CLIENT.send_control(mac, payload)
            
        # UI-Feedback: Wir "erwarten" den Modus (optional: leichtes Dimmen der Buttons)
        # Aber wir setzen NICHT die finale 'Active'-Farbe.

    def update_ui(self, *_):
        # 1. Grundlegende Sicherheits-Checks
        if not self._init_done or not getattr(WEB_CLIENT, "ready", False):
            return
        
        mac = GLOBAL_STATE.get_active_device_id()
        server_data = WEB_CLIENT.current_data.get(mac) if mac else None
        if not server_data: 
            return
    
        # --- 2. DAS TARGET-REVISION-GESETZ ---
        server_rev = int(server_data.get('rev', 0))
        last_sent = getattr(self, '_last_sent_rev', 0)
        
        # Zeit-Faktor: Wie lange ist die letzte Interaktion her?
        time_since_action = time.time() - self._last_user_action
        
        # SYNC-BEDINGUNG: Wir sind nur synchron, wenn der Server unsere Rev bestätigt hat
        # UND der User nicht gerade aktiv am Slider schiebt.
        is_synced = (server_rev >= last_sent) and not self._user_active and (time_since_action > 2.0)

        # IST-WERTE (Diese zeigen wir IMMER an, egal ob Sync oder nicht)
        arduino_effective = server_data.get('light_pct', 0)
        self.lbl_val.text = f"{int(arduino_effective)}%"

        if not is_synced:
            # STATUS: ORANGE (Warten auf Hardware-Bestätigung)
            self.sync_icon.text = "[font=FA]\uf021[/font]" # Spin/Sync Icon
            self.sync_icon.color = (1, 0.5, 0, 1)          # Orange
            
            # BLOCKADE: Wir springen hier raus. Die Slider bleiben auf der 
            # Position, die der User gewählt hat, bis der ESP32 "OK" sagt.
            return 
    
        # --- 3. SYNC OK: Hardware hat Target bestätigt ---
        self.sync_icon.text = "[font=FA]\uf058[/font]" # Check-Circle
        self.sync_icon.color = (0, 1, 0, 1)             # Grün
    
        # Werte vom Server extrahieren (Das sind jetzt die validierten Targets)
        arduino_target = server_data.get('light_target', 0)
        arduino_mode = server_data.get('light_mode', 'man')
        
        srv_h = server_data.get('l_start_h', 8)
        srv_m = server_data.get('l_start_m', 0)
        srv_dur = server_data.get('l_dur', 720)  # MINUTEN
        srv_sunrise = server_data.get('l_sunrise', 60)  # MINUTEN
        srv_sunset = server_data.get('l_sunset', 60)    # MINUTEN
    
        # --- 4. SLIDER SYNCHRONISATION ---
        if abs(self.slider.value - arduino_target) > 0.5:
            self.slider.value = arduino_target
    
        target_step = (srv_h * 60 + srv_m) // 15
        if abs(self.slider_start.value - target_step) >= 1:
            self.slider_start.value = target_step
    
        # FIX: Sunrise/Sunset Mapping korrekt (REIHENFOLGE KRITISCH!)
        # 1. ERST die Dauer setzen, damit range_max aktuell ist
        srv_dur_steps = srv_dur // 15
        if abs(self.slider_dur.value - srv_dur_steps) >= 1:
            self.slider_dur.value = srv_dur_steps
            # WICHTIG: Range_max sofort nachziehen
            self.slider_sunrise_sunset.range_max = srv_dur_steps
        
        # 2. Sunrise (linker Punkt)
        sr_steps = srv_sunrise // 15
        if abs(self.slider_sunrise_sunset.min_value - sr_steps) >= 1:
            self.slider_sunrise_sunset.min_value = sr_steps
        
        # 3. Sunset (rechter Punkt)
        ss_steps = srv_sunset // 15
        # Der Zielwert für den Slider-Handle ist: Aktuelle Range - Sunset-Abstand
        ss_max_val = self.slider_sunrise_sunset.range_max - ss_steps
        if abs(self.slider_sunrise_sunset.max_value - ss_max_val) >= 1:
            self.slider_sunrise_sunset.max_value = ss_max_val
    
        # --- 5. MODUS & BUTTON STYLES ---
        # Die Buttons leuchten erst hier final im korrekten Modus auf
        self._apply_button_styles(arduino_mode)
        
        # --- 6. STATUS TEXTE & SMART-INFOS ---
        remaining = server_data.get('light_remaining', -1)
        
        if arduino_mode == "tim":
            # Unterscheidung: Ist die Lampe laut Timer gerade an oder aus?
            is_active = arduino_effective > 0
            status_str = "AKTIV" if is_active else "SCHLÄFT"
            self.lbl_status_text.text = f"TIMER: {status_str} (Ziel: {int(arduino_target)}%)"
            self.lbl_status_text.color = (0, 1, 0, 1) if is_active else (0.3, 0.6, 1, 1)
            
            if remaining >= 0:
                h_rem = remaining // 60
                m_rem = remaining % 60
                time_str = f"{h_rem}h {m_rem}m" if h_rem > 0 else f"{m_rem} min"
                self.lbl_remaining.text = f"Nächster Schaltpunkt in: {time_str}"
            else:
                self.lbl_remaining.text = ""
        else:
            self.lbl_status_text.text = "MODUS: MANUELL"
            self.lbl_status_text.color = (1, 1, 1, 0.6)
            self.lbl_remaining.text = "Timer deaktiviert"


    
    def _apply_button_styles(self, mode):
        """
        Setzt die Button-Farben basierend auf dem vom ESP32 bestätigten Modus.
        Keine weiße Standard-Optik, sondern Dark-Mode mit Glow-Effekt.
        """
        # Farben definieren (RGBA)
        color_active_man = (0, 1, 0, 0.8)    # Kräftiges Neon-Grün
        color_active_tim = (0, 0.6, 1, 0.8)  # Elektro-Blau
        color_active_off = (1, 0.2, 0.2, 0.8) # Warn-Rot für AUS
        color_inactive   = (0.15, 0.15, 0.15, 1) # Tiefes Anthrazit (Hintergrund)
        color_text_dim   = (0.5, 0.5, 0.5, 1)    # Grauer Text für inaktive Buttons
        color_text_on    = (1, 1, 1, 1)          # Weißer Text für aktive Buttons

        # MANUELL Button
        if mode == "man":
            self.btn_man.background_color = color_active_man
            self.btn_man.color = color_text_on
            self.btn_man.text = "[b]MANUELL[/b]"
        else:
            self.btn_man.background_color = color_inactive
            self.btn_man.color = color_text_dim
            self.btn_man.text = "MANUELL"

        # TIMER Button
        if mode == "tim":
            self.btn_tim.background_color = color_active_tim
            self.btn_tim.color = color_text_on
            self.btn_tim.text = "[b]TIMER[/b]"
        else:
            self.btn_tim.background_color = color_inactive
            self.btn_tim.color = color_text_dim
            self.btn_tim.text = "TIMER"

        # AUS/STOP Button (Sonderlogik: Leuchtet nur kurz bei Action oder wenn Helligkeit 0)
        # Hier checken wir zusätzlich das Target, um "AUS" zu markieren
        is_off = (self.slider.value < 1 and mode == "man")
        if is_off:
            self.btn_off.background_color = color_active_off
            self.btn_off.color = color_text_on
        else:
            self.btn_off.background_color = color_inactive
            self.btn_off.color = color_text_dim

    def _create_styled_btn(self, text):
        """
        Erstellt das Grund-Styling für die Buttons beim Initialisieren.
        """
        return Button(
            text=text,
            markup=True,
            background_normal="", # Entfernt den Kivy-Standard-Verlauf
            background_color=(0.15, 0.15, 0.15, 1),
            color=(0.5, 0.5, 0.5, 1),
            bold=False,
            font_size=sp_scaled(12),
            background_down="", # Verhindert das hässliche Grau beim Klicken
        )
    def _sync_to_client(self, dt):
        if not self._pending_updates: return
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac: return
    
        sync_path = os.path.join(config.DATA, "settings_sync.json")
        
        # 1. Sicher Laden (falls Datei kaputt oder leer)
        data = {}
        if os.path.exists(sync_path):
            try:
                with open(sync_path, "r") as f:
                    content = f.read()
                    if content: # Prüfen ob nicht leer
                        data = json.loads(content)
            except Exception:
                data = {}
    
        # 2. Update einpflegen
        if mac not in data: data[mac] = {}
        data[mac].update(self._pending_updates)
        
        # 3. ATOMARES SPEICHERN
        try:
            tmp_path = sync_path + ".tmp"
            with open(tmp_path, "w") as f:
                json.dump(data, f)
            os.replace(tmp_path, sync_path) # Das hier ist der Zaubertrick
        except Exception as e:
            print(f"Write Error: {e}")
        
        self._pending_updates.clear()

    def _on_slider_change(self, instance, value):
        if not self._init_done: return
        # NUR die lokale Anzeige updaten, damit es flüssig aussieht
        self.lbl_val.text = f"{int(value)}%"
        
        # Icon auf Orange (User werkelt gerade)
        self.sync_icon.text = "[font=FA]\uf021[/font]"
        self.sync_icon.color = (1, 0.5, 0, 1)

    def _touch_up(self, slider, touch):
        if slider.collide_point(*touch.pos) or self._user_active:
            self._user_active = False
            self._last_user_action = time.time()
            self._intended_mode = "man"
            new_rev = int(time.time())
            self._last_sent_rev = new_rev
    
            mac = GLOBAL_STATE.get_active_device_id()
            if not mac:
                return False
    
            # 🔥 IMMER KOMPLETTE TIMER STATE BILDEN
            start_step = int(self.slider_start.value)
            total_min = start_step * 15
    
            h = total_min // 60
            m = total_min % 60
            
            # MODE BESTIMMEN
            current_mode = "man"
            if self.btn_tim.background_color[1] > 0.5:
                current_mode = "tim"
            
            # Sunrise/Sunset in Minuten aus 2-Punkt Slider (15er-Raster)
            sr_steps = int(self.slider_sunrise_sunset.min_value)
            ss_steps = int(self.slider_sunrise_sunset.range_max - self.slider_sunrise_sunset.max_value)
            sr_min = sr_steps * 15
            ss_min = ss_steps * 15
            
            # Dauer in Minuten
            dur_steps = int(self.slider_dur.value)
            dur_min = dur_steps * 15
            
            payload = {
                "light_pct": int(self.slider.value),

                "l_start_h": h,
                "l_start_m": m,
                "l_dur": dur_min,      # MINUTEN
                "l_sunrise": sr_min,   # MINUTEN
                "l_sunset": ss_min,    # MINUTEN

                "light_mode": current_mode,

                "rev": new_rev
            }
            WEB_CLIENT.send_control(mac, payload)
    
            return False
    
    def _on_sunrise_sunset_change(self, instance, value):
        """Callback für 2-Punkt Sunrise/Sunset Slider (in Minuten, 15er-Raster)"""
        sr_steps = int(self.slider_sunrise_sunset.min_value)
        ss_steps = int(self.slider_sunrise_sunset.range_max - self.slider_sunrise_sunset.max_value)
        sr_min = sr_steps * 15
        ss_min = ss_steps * 15
        
        sr_h = sr_min // 60
        sr_m = sr_min % 60
        ss_h = ss_min // 60
        ss_m = ss_min % 60
        
        self.lbl_sunrise_sunset.text = f"[font=FA]\uf185[/font] SUNRISE: {sr_h}h {sr_m:02d}m ↑ / [font=FA]\uf186[/font] SUNSET: {ss_h}h {ss_m:02d}m ↓"
        
        self.sync_icon.text = "[font=FA]\uf021[/font]"
        self.sync_icon.color = (1, 0.5, 0, 1)
    
    def _on_start_change(self, instance, value):
        step = int(value)
        total_min = step * 15
        
        h = total_min // 60
        m = total_min % 60
        
        self.lbl_start.text = f"START: {h:02d}:{m:02d}"
    
    
    def _on_dur_change(self, instance, value):
        """Dauer in 15-Minuten-Schritten"""
        steps = int(value)  # Jeder Step = 15 Minuten
        minutes = steps * 15
        hours = minutes // 60
        mins = minutes % 60
        
        self.lbl_dur.text = f"DAUER: {minutes} min" if minutes < 60 else f"DAUER: {hours}h {mins:02d}m"
        
        # KRITISCH: Bevor wir range_max ändern, merken wir uns den alten Sunset-Abstand
        old_max = self.slider_sunrise_sunset.range_max
        old_ss_steps = old_max - self.slider_sunrise_sunset.max_value
        
        # Jetzt den neuen Bereich setzen
        self.slider_sunrise_sunset.range_max = steps
        
        # Den rechten Slider-Punkt proportional anpassen (Sunset-Abstand bleibt gleich)
        new_max_val = steps - old_ss_steps
        if new_max_val < self.slider_sunrise_sunset.min_value:
            new_max_val = self.slider_sunrise_sunset.min_value + 1
        
        self.slider_sunrise_sunset.max_value = max(0, new_max_val)

    def _touch_down(self, slider, touch):
        if slider.collide_point(*touch.pos): self._user_active = True


    def _u(self, *_):
        self.bg_rect.pos = self.panel.pos
        self.bg_rect.size = self.panel.size
        self.outline.rounded_rectangle = (self.panel.x, self.panel.y, self.panel.width, self.panel.height, dp_scaled(20))

    def close(self):
        if self._update_event: self._update_event.cancel()
        if self._sync_event: self._sync_event.cancel()
        if self.parent: self.parent.remove_widget(self)
        GLOBAL_STATE.ui_handler.active_light_overlay = None

    def _init_values(self, *_):
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac:
            return
        
        arduino_data = WEB_CLIENT.current_data.get(mac, {})
        
        if not arduino_data:
            Clock.schedule_once(self._init_values, 0.3)
            return
    
        mode = arduino_data.get("light_mode", "man")
        val = arduino_data.get("light_target", 0)
    
        # Startzeit laden (h und m)
        h = arduino_data.get("l_start_h", 8)
        m = arduino_data.get("l_start_m", 0)
        step = (h * 60 + m) // 15  # Konvertierung zu 15-min Steps
    
        # Dauer laden (jetzt in Minuten!)
        dur_min = arduino_data.get("l_dur", 720)  # Default 12h = 720 min
        dur_steps = dur_min // 15  # Konvertierung zu Steps
        
        # UI setzen
        self.slider.value = val
        self.slider_start.value = step
        self.slider_dur.value = dur_steps
        
        # 2-Punkt Sunrise/Sunset Slider laden (in Minuten!)
        sr_min = arduino_data.get("l_sunrise", 60)  # Minuten
        ss_min = arduino_data.get("l_sunset", 60)   # Minuten
        sr_steps = sr_min // 15
        ss_steps = ss_min // 15
        
        self.slider_sunrise_sunset.min_value = sr_steps
        # max_value = range_max - ss_steps (vom Ende!)
        self.slider_sunrise_sunset.max_value = self.slider_sunrise_sunset.range_max - ss_steps
        
        # Label Update
        sr_h = sr_min // 60
        sr_m = sr_min % 60
        ss_h = ss_min // 60
        ss_m = ss_min % 60
        self.lbl_sunrise_sunset.text = f"[font=FA]\uf185[/font] SUNRISE: {sr_h}h {sr_m:02d}m ↑ / [font=FA]\uf186[/font] SUNSET: {ss_h}h {ss_m:02d}m ↓"
    
        self._apply_button_styles(mode)
    
        self.lbl_val.text = f"{int(val)}%"
        self.lbl_val.color = (1, 1, 1, 1)
        self.slider.disabled = False
    
        self._pending_updates.clear()
        self._init_done = True
    def _update_button_colors(self, mode):
        # Blau für Timer (wie im Browser), Grün für Manuell
        self.btn_man.background_color = (0, 1, 0, 0.6) if mode == "man" else (0.2, 0.2, 0.2, 1)
        self.btn_tim.background_color = (0, 0.5, 1, 0.8) if mode == "tim" else (0.2, 0.2, 0.2, 1)
