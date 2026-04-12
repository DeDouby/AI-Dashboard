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

class ExhaustFanOverlay(FloatLayout):
    def __init__(self, parent_header, **kwargs):
        super().__init__(**kwargs)
        self.parent_header = parent_header
        self._pending_updates = {} 
        self._user_active = False 
        self._last_user_action = 0 
        self._init_done = False
        self._last_sent_rev = 0
        self.sync_path = os.path.join(config.DATA, "settings_sync.json")

        self._update_event = Clock.schedule_interval(self.update_ui, 1.0)
        self._sync_event = Clock.schedule_interval(self._sync_to_client, 1.3)
# === NEU: Lock System ===
        self._locked = True
        self._lock_overlay = None
        # Hintergrund + Panel (Layout bleibt gleich)
        bg = Button(background_color=(0, 0, 0, 0.25))
        bg.bind(on_release=lambda *_: self.close())
        self.add_widget(bg)

        self.panel = BoxLayout(
            orientation="vertical", 
            spacing=dp_scaled(8),
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

        # Titel
        title_row = BoxLayout(size_hint_y=None, height=dp_scaled(40), spacing=dp_scaled(5))
        self.lbl_title = Label(text="EXHAUST FAN CONTROL", bold=True, color=(0, 1, 0, 1),
                               font_size=sp_scaled(15), halign="left", valign="middle")
        self.lbl_title.bind(size=self.lbl_title.setter('text_size'))
        
        self.sync_icon = Button(text="[font=FA]\uf021[/font]", markup=True,
                                font_size=sp_scaled(30), size_hint=(None, None), 
                                width=dp_scaled(45), height=dp_scaled(45),
                                background_normal="", background_down="", 
                                background_color=(0, 0, 0, 0), color=(1, 1, 1, 1))
        self.sync_icon.bind(on_release=self._force_sync)
        
        title_row.add_widget(self.lbl_title)
        title_row.add_widget(self.sync_icon)
        self.panel.add_widget(title_row)

        # Wert-Anzeige
        self.lbl_val = Label(text="0% - 0%", font_size=sp_scaled(36), bold=True, 
                             size_hint_y=None, height=dp_scaled(50))
        self.panel.add_widget(self.lbl_val)

        # Live Info
        info_row = BoxLayout(size_hint_y=None, height=dp_scaled(20), spacing=dp_scaled(10))
        self.lbl_rpm = Label(text="RPM: 0", font_size=sp_scaled(15), color=(0.7, 0.7, 1, 0.8))
        self.lbl_live_speed = Label(text="LIVE: 0%", font_size=sp_scaled(15), bold=True, color=(0, 1, 1, 0.8))
        info_row.add_widget(self.lbl_rpm)
        info_row.add_widget(self.lbl_live_speed)
        self.panel.add_widget(info_row)

        # Slider-Bereich
        self.panel.add_widget(Widget(size_hint_y=None, height=dp_scaled(5)))

        self.panel.add_widget(Label(text="FAN SPEED RANGE", font_size=sp_scaled(15), 
                                   color=(0,1,0,0.5), size_hint_y=None, height=dp_scaled(12)))
        self.range_slider = UnifiedSlider(min=0, max=100, mode='range', 
                                          size_hint_y=None, height=dp_scaled(40))
        self.range_slider.bind(min_value=self._on_slider_change, max_value=self._on_slider_change,
                               on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.range_slider)

        # Temp Slider
        temp_head = BoxLayout(size_hint_y=None, height=dp_scaled(12))
        temp_head.add_widget(Label(text="TEMP TARGET", font_size=sp_scaled(15), color=(0,1,0,0.5), halign="left"))
        self.lbl_temp = Label(text="22° - 28°", font_size=sp_scaled(15), color=(1,1,1,0.6), halign="right")
        temp_head.add_widget(self.lbl_temp)
        self.panel.add_widget(temp_head)

        self.temp_slider = UnifiedSlider(range_min=15, range_max=35, min=22, max=28, mode='range', 
                                         size_hint_y=None, height=dp_scaled(40))
        self.temp_slider.bind(min_value=self._on_env_slider_change, max_value=self._on_env_slider_change,
                              on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.temp_slider)

        # Humidity Slider
        hum_head = BoxLayout(size_hint_y=None, height=dp_scaled(12))
        hum_head.add_widget(Label(text="HUMIDITY TARGET", font_size=sp_scaled(15), color=(0,1,0,0.5), halign="left"))
        self.lbl_hum = Label(text="40% - 70%", font_size=sp_scaled(15), color=(1,1,1,0.6), halign="right")
        hum_head.add_widget(self.lbl_hum)
        self.panel.add_widget(hum_head)

        self.hum_slider = UnifiedSlider(min=0, max=100, mode='range', 
                                        size_hint_y=None, height=dp_scaled(40))
        self.hum_slider.bind(min_value=self._on_env_slider_change, max_value=self._on_env_slider_change,
                             on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.hum_slider)

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

        Clock.schedule_once(self._init_values, 0.1)
        
        # Lock-Maske aktivieren
        Clock.schedule_once(lambda dt: self._create_lock_overlay(), 0.4)
        
        self.add_widget(self.panel)

    def _create_styled_btn(self, text):
        return Button(
            text=text, markup=True, background_normal="", 
            background_color=(0.15, 0.15, 0.15, 1),
            color=(0.5, 0.5, 0.5, 1), bold=False,
            font_size=sp_scaled(15), background_down=""
        )


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
# ====================== UPDATE ======================
    def update_ui(self, *_):
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

        # Live Werte immer updaten
        srv_live = server_data.get('exhaust_fan_speed_now', 0)
        srv_rpm = server_data.get('exhaust_fan_rpm', 0)
        self.lbl_rpm.text = f"RPM: {int(srv_rpm)}"
        self.lbl_live_speed.text = f"LIVE: {int(srv_live)}%"

        if not is_synced:
            self.sync_icon.text = "[font=FA]\uf021[/font]"
            self.sync_icon.color = (1, 0.5, 0, 1)
            return

        # Synced → alles nachziehen
        self.sync_icon.text = "[font=FA]\uf058[/font]"
        self.sync_icon.color = (0, 1, 0, 1)

        srv_min = int(server_data.get('exhaust_fan_min', 20))
        srv_max = int(server_data.get('exhaust_fan_pct', 65))
        srv_mode = server_data.get('exhaust_fan_mode', 'auto')

        t_min = max(15, min(35, int(server_data.get('target_temp_min', 22))))
        t_max = max(15, min(35, int(server_data.get('target_temp_max', 28))))
        h_min = int(server_data.get('target_humidity_min', 40))
        h_max = int(server_data.get('target_humidity_max', 70))

        self.lbl_val.text = f"{srv_min}% - {srv_max}%"
        self.lbl_temp.text = f"Temp: {t_min}° - {t_max}°"
        self.lbl_hum.text = f"Hum: {h_min}% - {h_max}%"

        # Slider sanft nachziehen
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

        self._apply_button_styles(srv_mode)

    def _apply_button_styles(self, mode):
        c_bg = (0.15, 0.15, 0.15, 1)
        self.btn_man.background_color  = (0, 1, 0, 0.8) if mode == "man"  else c_bg
        self.btn_auto.background_color = (0, 0.7, 1, 0.8) if mode == "auto" else c_bg
        self.btn_chao.background_color = (1, 0.5, 0, 0.8) if mode == "chao" else c_bg

        for btn in (self.btn_man, self.btn_auto, self.btn_chao):
            btn.color = (1, 1, 1, 1) if btn.background_color[1] > 0.5 or btn.background_color[0] > 0.8 else (0.6, 0.6, 0.6, 1)

    # Die restlichen Methoden (_on_slider_change, _on_env_slide

    
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
        if self._locked:
            return
            
        """Setzt den Modus und sendet sofort an den Server"""
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac:
            return
        
        now = time.time()
        new_rev = int(now)
        self._last_sent_rev = new_rev 
        self._last_user_action = now  

        self._apply_button_styles(mode)
        self.sync_icon.text = "[font=FA]\uf021[/font]"
        self.sync_icon.color = (1, 0.5, 0, 1)

        payload = {
            "exhaust_fan_min": int(self.range_slider.min_value),
            "exhaust_fan_pct": int(self.range_slider.max_value),
            "exhaust_fan_target": int(self.range_slider.max_value),
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
        if self._locked:
            return False
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
        GLOBAL_STATE.ui_handler.active_exhaust_fan_overlay = None

# ====================== INITIALISIERUNG (JETZT STARK) ======================
    def _init_values(self, *_):
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac:
            Clock.schedule_once(self._init_values, 0.5)
            return

        server_data = WEB_CLIENT.current_data.get(mac, {})
        
        if not server_data:
            Clock.schedule_once(self._init_values, 0.4)
            return

        # Werte laden mit sinnvollen Defaults
        saved_min = int(server_data.get("exhaust_fan_min", 20))
        saved_max = int(server_data.get("exhaust_fan_pct", 65))
        saved_mode = server_data.get("exhaust_fan_mode", "auto")

        t_min = int(server_data.get("target_temp_min", 22))
        t_max = int(server_data.get("target_temp_max", 28))
        h_min = int(server_data.get("target_humidity_min", 40))
        h_max = int(server_data.get("target_humidity_max", 70))

        # Slider setzen
        self.range_slider.min_value = saved_min
        self.range_slider.max_value = saved_max
        
        self.temp_slider.min_value = max(15, min(35, t_min))
        self.temp_slider.max_value = max(15, min(35, t_max))
        
        self.hum_slider.min_value = h_min
        self.hum_slider.max_value = h_max

        # Labels
        self.lbl_val.text = f"{saved_min}% - {saved_max}%"
        self.lbl_temp.text = f"Temp: {t_min}° - {t_max}°"
        self.lbl_hum.text = f"Hum: {h_min}% - {h_max}%"

        self._apply_button_styles(saved_mode)
        
        self._init_done = True
        self._last_sent_rev = int(server_data.get('rev', 0))
        print(f"[Exhaust] Init erfolgreich: {saved_min}-{saved_max}% | Temp {t_min}-{t_max} | Hum {h_min}-{h_max} | Mode: {saved_mode}")

    def _create_lock_overlay(self):
        """Dezente Sperr-Maske nur über dem Panel - Exhaust Version"""
        if self._lock_overlay:
            return
        
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
        
        self.panel.bind(pos=self._update_lock_pos, size=self._update_lock_pos)
        self.add_widget(self._lock_overlay)

    def _update_lock_pos(self, *_):
        """Position der Lock-Maske mit dem Panel synchron halten"""
        if self._lock_overlay:
            self._lock_overlay.pos = self.panel.pos
            self._lock_overlay.size = self.panel.size

    def _unlock(self, *_):
        """Entsperrt das Exhaust Overlay"""
        if self._lock_overlay:
            self.remove_widget(self._lock_overlay)
            self._lock_overlay = None
        
        self._locked = False
        self.sync_icon.color = (0, 1, 0, 1)
        print("[Exhaust] Edit-Modus aktiviert")        