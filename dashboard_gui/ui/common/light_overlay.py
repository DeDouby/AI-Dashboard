from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.clock import Clock
from kivy.uix.scrollview import ScrollView
import config 
import time 
import json 
import os
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled

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
            size=(dp_scaled(420), dp_scaled(420)),  # etwas höher für mobile
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
            size_hint_y=None
        )
        
        self.content.bind(minimum_height=self.content.setter('height'))
        
        self.scroll.add_widget(self.content)
        self.content.add_widget(title_row)
        self.panel.add_widget(self.scroll)
        # --- WERTE-ANZEIGE ---
        # --- WERTE-ANZEIGE ---
        self.lbl_val = Label(text="SYNC...", font_size=sp_scaled(45), bold=True, color=(1, 0.5, 0, 1))
        self.content.add_widget(self.lbl_val)
        
        # Slider initial deaktivieren
        self.slider = Slider(
            min=0, max=100, step=1,
            size_hint_y=None, height=dp_scaled(45),
            disabled=True # <--- WICHTIG: Erst nach Sync freigeben
        )
        self.slider.bind(value=self._on_slider_change, on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.content.add_widget(self.slider)

        # Grow Stats
        self.stats_box = BoxLayout(orientation="vertical", spacing=dp_scaled(5), size_hint_y=None, height=dp_scaled(60))
        self.lbl_ppfd = Label(text="PPFD: 0 µmol/m²/s", font_size=sp_scaled(14), color=(0.7, 0.7, 1, 1))
        self.lbl_dli = Label(text="DLI: 0.0 mol/m²/d", font_size=sp_scaled(14), color=(0.7, 0.7, 1, 1))
        self.stats_box.add_widget(self.lbl_ppfd)
        self.stats_box.add_widget(self.lbl_dli)
        self.content.add_widget(self.stats_box)
        
        
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

        self.sunrise_box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp_scaled(60))
        
        self.lbl_sunrise = Label(text="SUNRISE: 30 min", font_size=sp_scaled(14))
        
        self.slider_sunrise = Slider(
            min=0, max=60, step=1,
            value=30,
            size_hint_y=None, height=dp_scaled(30)
        )
        self.slider_sunrise.bind(value=self._on_sunrise_change)
        
        self.sunrise_box.add_widget(self.lbl_sunrise)
        self.sunrise_box.add_widget(self.slider_sunrise)
        
        self.content.add_widget(self.sunrise_box)
        # --- TIMER-EINSTELLUNG (NEU: Wie im Browser) ---
        # --- TIMER-EINSTELLUNG (FLEXIBEL) ---
        self.timer_box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp_scaled(120), spacing=dp_scaled(5))
        
        # STARTZEIT (15 MIN RASTER)
        self.lbl_start = Label(text="START: 08:00", font_size=sp_scaled(14))
        
        self.slider_start = Slider(
            min=0, max=95, step=1,  # 96 steps = 24h / 15min
            value=32,  # 08:00
            size_hint_y=None, height=dp_scaled(30)
        )
        self.slider_start.bind(value=self._on_start_change)
        
        # DAUER (0–24h)
        self.lbl_dur = Label(text="DAUER: 12 h", font_size=sp_scaled(14))
        
        self.slider_dur = Slider(
            min=0, max=24, step=1,
            value=12,
            size_hint_y=None, height=dp_scaled(30)
        )
        self.slider_dur.bind(value=self._on_dur_change)
        
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
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac: return
    
        print("[UI] FORCE SYNC: Sende aktuellen UI-Zustand als Master...")
    
        # Wir nehmen NICHT die Datei, sondern das, was wir GERADE SEHEN
        try:
            start_step = int(self.slider_start.value)
            total_min = start_step * 15
            
            h = total_min // 60
            m = total_min % 60
            
            d = int(self.slider_dur.value)
        except:
            h, d = 8, 12

        # Wir bestimmen den Modus anhand der Button-Farben/Logik
        # (Oder wir speichern den letzten gedrückten Modus in self.current_ui_mode)
        current_mode = "man"
        if self.btn_tim.background_color[1] > 0.5: current_mode = "tim"

        payload = {
            "light_pct": int(self.slider.value),
            "light_mode": current_mode,
            "l_start_h": h,
            "l_dur": d,
            "l_start_m": m,

            "l_sun": int(self.slider_sunrise.value),
            "rev": int(time.time()) # Neue Revision erzwingen
        }
    
        # Direkt raus damit
        WEB_CLIENT.send_control(mac, payload)
        
        # Optisches Feedback
        self.sync_icon.color = (1, 1, 0, 1)

    def update_ui(self, *_):
        
        if not getattr(WEB_CLIENT, "ready", False) or not self._init_done: 
            return # Nichts tun, solange _init_done nicht True ist
        # 1. Sicherheits-Checks
        
        now = time.time()
        if not self._init_done or self._user_active or (now - self._last_user_action < 2.0):
            return
        
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac: return
    
        # 2. Daten vom Web-Client holen
        server_data = WEB_CLIENT.current_data.get(mac)
        if not server_data: return
    
        # Werte extrahieren
        arduino_target = server_data.get('light_target', 0)
        arduino_effective = server_data.get('light_pct', 0)
        arduino_mode = server_data.get('light_mode', 'man')
        remaining = server_data.get('light_remaining', -1)
        server_rev = int(server_data.get('rev', 0))
    
        # --- 3. SYNC-CHECK (Das Herzstück) ---
        last_sent = getattr(self, '_last_sent_rev', 0)
        
        if server_rev < last_sent:
            # ESP ist noch beim alten Stand -> Bleib im Sync-Modus (Orange)
            self.sync_icon.text = "[font=FA]\uf021[/font]"
            self.sync_icon.color = (1, 0.5, 0, 1)
            # WICHTIG: Wir brechen hier NICHT ab, aber wir überspringen das 
            # Update der Button-Farben, damit diese nicht zurückspringen!
            sync_pending = True
        else:
            # Alles paletti -> Grün!
            self.sync_icon.text = "[font=FA]\uf058[/font]"
            self.sync_icon.color = (0, 1, 0, 1)
            sync_pending = False
    
        # --- 4. UI-ELEMENTE AKTUALISIEREN ---
        self.lbl_val.text = f"{int(arduino_effective)}%"
        
        # Slider nachziehen (nur wenn kein Sync aussteht)
        if not sync_pending and not self._pending_updates:
            if abs(self.slider.value - arduino_target) > 0.5:
                self.slider.value = arduino_target
    
        # Restzeit nur im Timer-Modus
        if arduino_mode == "tim" and remaining >= 0:
            self.lbl_remaining.text = f"Wechsel in: {remaining} Min."
        else:
            self.lbl_remaining.text = ""
    
        # Button-Farben NUR übernehmen, wenn der Sync abgeschlossen ist
        if not sync_pending:
            self._apply_button_styles(arduino_mode)
            
            # Titel-Farbe passend zum Modus
            if arduino_mode == "tim":
                self.lbl_title.text = "LIGHT CONTROL (TIMER)"
                self.lbl_title.color = (0, 0.7, 1, 1) # Blau
            else:
                self.lbl_title.text = "LIGHT CONTROL PRO"
                self.lbl_title.color = (0, 1, 0, 1) # Grün
    
        # 5. GROW-STATS
        ppfd = int(arduino_effective * 8.5) 
        self.lbl_ppfd.text = f"PPFD: {ppfd} µmol/m²/s"
        dli = (ppfd * 3600 * 12) / 1000000 
        self.lbl_dli.text = f"DLI: {dli:.1f} mol/m²/d"
    
    # Hilfsfunktion für die Button-Optik (um Code-Duplikate zu vermeiden)
    def _apply_button_styles(self, mode):
        self.btn_man.background_color = (0, 1, 0, 0.6) if mode == "man" else (0.2, 0.2, 0.2, 1)
        self.btn_tim.background_color = (0, 0.7, 1, 0.6) if mode == "tim" else (0.2, 0.2, 0.2, 1)
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
        self.lbl_val.text = f"{int(value)}%"
        
        # SOFORT-FEEDBACK: UI geht auf "Syncing" (Orange)
        self.sync_icon.text = "[font=FA]\uf021[/font]"
        self.sync_icon.color = (1, 0.5, 0, 1) # Sattes Orange
        
        mac = GLOBAL_STATE.get_active_device_id()
        if mac:
            # Wir generieren eine neue Revision basierend auf dem Zeitstempel
            new_rev = int(time.time())
            payload = {
                "light_pct": int(value),
                "rev": new_rev
            }
            # Wir merken uns die Revision lokal, um sie mit dem nächsten /data zu vergleichen
            self._last_sent_rev = new_rev 
            WEB_CLIENT.send_control(mac, payload)

    def _on_sunrise_change(self, instance, value):
        val = int(value)
        self.lbl_sunrise.text = f"SUNRISE: {val} min"
    
    
    def _on_start_change(self, instance, value):
        step = int(value)
        total_min = step * 15
        
        h = total_min // 60
        m = total_min % 60
        
        self.lbl_start.text = f"START: {h:02d}:{m:02d}"
    
    
    def _on_dur_change(self, instance, value):
        val = int(value)
        self.lbl_dur.text = f"DAUER: {val} h"
    def _set_mode(self, mode):
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac: return

        # 1. Werte sicher aus den TextInputs auslesen
        try:
            start_step = int(self.slider_start.value)
            total_min = start_step * 15
            
            h = total_min // 60
            m = total_min % 60
            
            d = int(self.slider_dur.value)
            s = int(self.slider_sunrise.value)
        except Exception as e:
            print(f"[UI] Fehler beim Lesen der Timer-Felder: {e}")
            h, m, d, s = 8, 0, 12, 30 # Fallback-Werte, falls ein Feld leer ist

        # 2. Visuelles Feedback
        self.sync_icon.text = "[font=FA]\uf021[/font]"
        self.sync_icon.color = (1, 0.5, 0, 1) # Orange
        
        # 3. Neue Revision
        new_rev = int(time.time())
        self._last_sent_rev = new_rev 

        # 4. Payload bauen (jetzt mit definiertem 's')
        payload = {
            "light_mode": mode,
            "l_start_h": h,
            "l_start_m": m,
            "l_dur": d,
            "l_sun": s,     # <--- Jetzt kennt er 's'
            "rev": new_rev
        }

        # 5. Absenden
        WEB_CLIENT.send_control(mac, payload)
        
        # 6. Button-Styles vorab anpassen
        self._apply_button_styles(mode)

    def _touch_down(self, slider, touch):
        if slider.collide_point(*touch.pos): self._user_active = True

    def _touch_up(self, slider, touch):
        # Wir prüfen nicht nur collide_point, sondern setzen den Timestamp immer, 
        # wenn der Slider losgelassen wird.
        if slider.collide_point(*touch.pos) or self._user_active:
            self._user_active = False
            self._last_user_action = time.time() # Startet den 2-Sekunden-Countdown
            
            # OPTIONAL: Schicke den Wert beim Loslassen noch einmal zur Sicherheit
            self._on_slider_change(slider, slider.value)
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
        if not mac: return
        
        # Hol dir die aktuellen Daten
        arduino_data = WEB_CLIENT.current_data.get(mac, {})
        
        # PRÜFUNG: Haben wir echte Daten oder nur ein leeres Dictionary?
        if not arduino_data or "light_target" not in arduino_data:
            # Noch keine Daten da? In 0.2 Sekunden nochmal probieren
            Clock.schedule_once(self._init_values, 0.2)
            return
    
        # WENN WIR HIER SIND, HABEN WIR DATEN!
        mode = arduino_data.get("light_mode", "man")
        val = arduino_data.get("light_target", 0)
        
        # UI befüllen
        self.slider.value = val
        h = arduino_data.get("light_timer_start", 8)
        m = arduino_data.get("light_timer_start_m", 0)
        
        step = (h * 60 + m) // 15
        self.slider_start.value = step
        
        self.slider_dur.value = arduino_data.get("light_timer_dur", 12)
        self.slider_sunrise.value = arduino_data.get("light_sunrise_min", 30)
        self._apply_button_styles(mode)
        
        # UI "scharf" schalten
        self.lbl_val.text = f"{int(val)}%"
        self.lbl_val.color = (1, 1, 1, 1) # Wieder weiß/normal
        self.slider.disabled = False
        
        self._pending_updates.clear()
        self._init_done = True

    def _update_button_colors(self, mode):
        # Blau für Timer (wie im Browser), Grün für Manuell
        self.btn_man.background_color = (0, 1, 0, 0.6) if mode == "man" else (0.2, 0.2, 0.2, 1)
        self.btn_tim.background_color = (0, 0.5, 1, 0.8) if mode == "tim" else (0.2, 0.2, 0.2, 1)
