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

# WICHTIG: Den globalen Client importieren
from web_client import WEB_CLIENT 

class ExhaustFanOverlay(FloatLayout):
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
            size=(dp_scaled(420), dp_scaled(500)),
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
            text="EXHAUST FAN CONTROL", 
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
            background_down="", 
            background_color=(0, 0, 0, 0), 
            color=(1, 1, 1, 1) 
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


        # NEU: Das Live-Output Label
        self.lbl_live_speed = Label(
            text="LIVE OUTPUT: 0%", 
            font_size=sp_scaled(22), 
            bold=True, 
            color=(0, 1, 1, 1) # Ein schickes Cyan/Blau für den Ist-Wert
        )
        self.panel.add_widget(self.lbl_live_speed)


        # --- SPEED RANGE SLIDER ---
        self.panel.add_widget(Label(text="SPEED RANGE (MIN - MAX)", font_size=sp_scaled(11), color=(0,1,0,0.5), size_hint_y=None, height=dp_scaled(15)))
        
        self.range_slider = UnifiedSlider(min=0, max=100, range_min=0, range_max=100, mode='range', size_hint_y=None, height=dp_scaled(45))
        self.range_slider.bind(min_value=self._on_slider_change, max_value=self._on_slider_change)
        self.range_slider.bind(on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.range_slider)

        # --- TEMP RANGE (HIER WAR DIE LÜCKE) ---
        self.panel.add_widget(Label(
            text="TEMP TARGET RANGE", 
            font_size=sp_scaled(11), 
            color=(0,1,0,0.5),
            size_hint_y=None, height=dp_scaled(15)
        ))
        
        self.temp_slider = UnifiedSlider(min=15, max=30, range_min=15, range_max=30, mode='range', size_hint_y=None, height=dp_scaled(45))
        self.temp_slider.bind(min_value=self._on_env_slider_change, max_value=self._on_env_slider_change)
        self.temp_slider.bind(on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.temp_slider)
        
        self.lbl_temp = Label(text="Temp: 0° - 0°", font_size=sp_scaled(14))
        self.panel.add_widget(self.lbl_temp)
        
        # --- HUMIDITY RANGE ---
        self.panel.add_widget(Label(
            text="HUMIDITY TARGET RANGE", 
            font_size=sp_scaled(11), 
            color=(0,1,0,0.5),
            size_hint_y=None, height=dp_scaled(15)
        ))
        
        self.hum_slider = UnifiedSlider(min=0, max=100, range_min=0, range_max=100, mode='range', size_hint_y=None, height=dp_scaled(45))
        self.hum_slider.bind(min_value=self._on_env_slider_change, max_value=self._on_env_slider_change)
        self.hum_slider.bind(on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.hum_slider)
        
        self.lbl_hum = Label(text="Hum: 0% - 0%", font_size=sp_scaled(14))
        self.panel.add_widget(self.lbl_hum)

        # --- MODI-BUTTONS ---
        # Modi-Buttons
        btn_row = BoxLayout(size_hint_y=None, height=dp_scaled(45), spacing=dp_scaled(10))
        self.btn_man = self._create_styled_btn("MANUAL")
        self.btn_auto = self._create_styled_btn("AUTOMATIC")
        self.btn_chao = self._create_styled_btn("CHAOTIC")
        
        self.btn_man.bind(on_release=lambda *_: self._set_mode("man"))
        self.btn_auto.bind(on_release=lambda *_: self._set_mode("auto"))
        self.btn_chao.bind(on_release=lambda *_: self._set_mode("chao"))
        
        btn_row.add_widget(self.btn_man); btn_row.add_widget(self.btn_auto); btn_row.add_widget(self.btn_chao)
        self.panel.add_widget(btn_row)


        
        Clock.schedule_once(self._init_values, 0)
        self.add_widget(self.panel)

    def _create_styled_btn(self, text):
        return Button(text=text, background_normal="", background_color=(0.2, 0.2, 0.2, 1), 
                      bold=True, font_size=sp_scaled(10))



    def _on_env_slider_change(self, *_):
        if not self._init_done: return
    
        t_min, t_max = int(self.temp_slider.min_value), int(self.temp_slider.max_value)
        h_min, h_max = int(self.hum_slider.min_value), int(self.hum_slider.max_value)
    
        self.lbl_temp.text = f"Temp: {t_min}° - {t_max}°"
        self.lbl_hum.text = f"Hum: {h_min}% - {h_max}%"
    
        # Sync Icon Orange signalisiert: UI ist weiter als Hardware
        self.sync_icon.text = "[font=FA]\uf021[/font]"
        self.sync_icon.color = (1, 0.5, 0, 1)
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
        
        print(f"[UI] FORCE SYNC EXHAUST: Sende aktuellen Slider-Stand {int(self.range_slider.min_value)}-{int(self.range_slider.max_value)}% als Master...")
        
        # Wir holen die Werte direkt von der UI, NICHT aus einer alten Datei
        min_v = int(self.range_slider.min_value)
        max_v = int(self.range_slider.max_value)
        
        # Modus bestimmen (wir schauen, welcher Button gerade aktiv/grün leuchtet)
# 1. Modus anhand der Button-Farben bestimmen
        current_mode = "man" # Default, falls nichts passt
        
        # Wir prüfen, welcher Button gerade die "aktive" Farbe hat
        if self.btn_auto.background_color[1] > 0.5: 
            current_mode = "auto"
        elif self.btn_chao.background_color[0] > 0.5: # Chaotic ist oft Orange/Rot-lastig
            current_mode = "chao"
        elif self.btn_man.background_color[1] > 0.5:
            current_mode = "man"

        new_rev = int(time.time())
        self._last_sent_rev = new_rev

        payload = {
            "exhaust_fan_min": min_v,
            "exhaust_fan_pct": max_v, # Dein Max-Wert
            "exhaust_fan_mode": current_mode,
            "exhaust_fan_target": max_v,
            "rev": new_rev
        }
        
        # Direkt an den Web-Client senden
        WEB_CLIENT.send_control(mac, payload)
        
        # Optisches Feedback: Icon wird gelb/orange bis der Server mit der neuen Rev antwortet
        self.sync_icon.text = "[font=FA]\uf021[/font]"
        self.sync_icon.color = (1, 1, 0, 1)
        
        # Zusätzlich das lokale File-Backup triggern
        self._pending_updates.update(payload)
        self._sync_to_client(0)

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
        srv_min = server_data.get('exhaust_fan_min', 0)
        srv_max = server_data.get('exhaust_fan_pct', 0) # 'pct' ist hier dein Max
        srv_mode = server_data.get('exhaust_fan_mode', 'man')
        srv_rpm = server_data.get('exhaust_fan_rpm', 0)
        server_rev = int(server_data.get('rev', 0))
        t_min = server_data.get('target_temp_min', 20)
        t_max = server_data.get('target_temp_max', 30)
        
        h_min = server_data.get('target_humidity_min', 40)
        h_max = server_data.get('target_humidity_max', 70)

        # HIER DEN LIVE-WERT HOLEN:
        srv_live = server_data.get('exhaust_fan_speed_now', 0)
        
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
        
        self.lbl_live_speed.text = f"LIVE OUTPUT: {int(srv_live)}%"
        self.lbl_temp.text = f"Temp: {int(t_min)}° - {int(t_max)}°"
        self.lbl_hum.text = f"Hum: {int(h_min)}% - {int(h_max)}%"
        # Slider nur nachziehen, wenn nicht gerade synchronisiert wird
        if not sync_pending:
            # Kleine Toleranz beim Vergleich (0.5)
            if abs(self.range_slider.min_value - srv_min) > 0.5:
                self.range_slider.min_value = srv_min
            if abs(self.range_slider.max_value - srv_max) > 0.5:
                self.range_slider.max_value = srv_max
            if abs(self.temp_slider.min_value - t_min) > 0.5:
                self.temp_slider.min_value = t_min
            if abs(self.temp_slider.max_value - t_max) > 0.5:
                self.temp_slider.max_value = t_max
            
            if abs(self.hum_slider.min_value - h_min) > 0.5:
                self.hum_slider.min_value = h_min
            if abs(self.hum_slider.max_value - h_max) > 0.5:
                self.hum_slider.max_value = h_max           
            # Button Farben setzen
            self._apply_button_styles(srv_mode)

    def _apply_button_styles(self, mode):
        # Hilfsfunktion für konsistente Farben
        self.btn_man.background_color = (0, 1, 0, 0.6) if mode == "man" else (0.2, 0.2, 0.2, 1)
        self.btn_auto.background_color = (0, 0.7, 1, 0.6) if mode == "auto" else (0.2, 0.2, 0.2, 1)
        self.btn_chao.background_color = (1, 0.5, 0, 0.6) if mode == "chao" else (0.2, 0.2, 0.2, 1)
    
    def _send_current_range_to_server(self):
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac: return
        
        # Erhöhung der lokalen Revision für das Target-Revision-Prinzip
        new_rev = int(time.time())
        self._last_sent_rev = new_rev
        
        payload = {
            "exhaust_fan_min": int(self.range_slider.min_value),
            "exhaust_fan_pct": int(self.range_slider.max_value), # Max Speed
            "target_temp_min": int(self.temp_slider.min_value),
            "target_temp_max": int(self.temp_slider.max_value),
            "target_humidity_min": int(self.hum_slider.min_value),
            "target_humidity_max": int(self.hum_slider.max_value),
            "rev": new_rev
        }
        
        WEB_CLIENT.send_control(mac, payload)
        self._pending_updates.update(payload)
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
            "exhaust_fan_min": int(self.range_slider.min_value),
            "exhaust_fan_pct": int(self.range_slider.max_value),
        
            "exhaust_fan_target": int(self.range_slider.max_value),  # ← FEHLTE
        
            "exhaust_fan_mode": mode,
        
            "target_temp_min": int(self.temp_slider.min_value),
            "target_temp_max": int(self.temp_slider.max_value),
        
            "target_humidity_min": int(self.hum_slider.min_value),
            "target_humidity_max": int(self.hum_slider.max_value),
        
            "rev": new_rev
        }
        WEB_CLIENT.send_control(mac, payload)
        
        self._pending_updates.update({"exhaust_fan_mode": mode, "rev": new_rev})
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
        GLOBAL_STATE.ui_handler.active_exhaust_fan_overlay = None

    def _init_values(self, *_):
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac: return
    
        # 1. Wir holen uns den AKTUELLEN Stand vom WEB_CLIENT Speicher (nicht nur File)
        server_data = WEB_CLIENT.current_data.get(mac, {})
        
        # Wenn der Server Daten hat, nehmen wir die als Basis für unsere UI
        if server_data:
            saved_min = server_data.get("exhaust_fan_min", 20)
            saved_max = server_data.get("exhaust_fan_pct", 60)
            saved_mode = server_data.get("exhaust_fan_mode", "auto")
        else:
            # Nur wenn gar nichts da ist, aus Datei oder Default
            saved_min = 20
            saved_max = 60
            saved_mode = "auto"
        self.temp_slider.min_value = server_data.get("target_temp_min", 22)
        self.temp_slider.max_value = server_data.get("target_temp_max", 28)

        self.hum_slider.min_value = server_data.get("target_humidity_min", 40)
        self.hum_slider.max_value = server_data.get("target_humidity_max", 70)
        self.range_slider.min_value = saved_min
        self.range_slider.max_value = saved_max
        self._set_mode_ui_only(saved_mode) # Neue Hilfsfunktion für Farben
    
        self._init_done = True
        # Der erste Sync erfolgt jetzt erst, wenn der User wirklich was drückt 
        # ODER wenn update_ui das erste Mal die Revisionen glattzieht.

    def _set_mode_ui_only(self, mode):
        self.btn_man.background_color = (0, 1, 0, 0.6) if mode == "man" else (0.2, 0.2, 0.2, 1)
        self.btn_auto.background_color = (0, 0.7, 1, 0.6) if mode == "auto" else (0.2, 0.2, 0.2, 1)
        self.btn_chao.background_color = (1, 0.2, 0.2, 0.6) if mode == "chao" else (0.2, 0.2, 0.2, 1)