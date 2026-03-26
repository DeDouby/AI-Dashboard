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

class LightOverlay(FloatLayout):
    def __init__(self, parent_header, **kwargs):
        super().__init__(**kwargs)
        self.parent_header = parent_header
        self._pending_updates = {} 
        self._user_active = False 
        self._last_user_action = 0 
        
        # Events wie beim Fan
        self._update_event = Clock.schedule_interval(self.update_ui, 1.0)
        self._sync_event = Clock.schedule_interval(self._sync_to_client, 1.3)

        # 1. HINTERGRUND-ABDUNKELUNG
        bg = Button(background_color=(0, 0, 0, 0.25))
        bg.bind(on_release=lambda *_: self.close())
        self.add_widget(bg)
        # Im Overlay beim Ändern:
        # 2. DAS PANEL
        self.panel = BoxLayout(
            orientation="vertical", 
            padding=dp_scaled(20), 
            spacing=dp_scaled(15),
            size_hint=(None, None), 
            size=(dp_scaled(320), dp_scaled(420)), # Etwas höher für die Stats
            pos_hint={"right": 0.98, "top": 0.98}
        )

        with self.panel.canvas.before:
            Color(0, 0, 0, 0.65)
            self.bg_rect = RoundedRectangle(radius=[dp_scaled(20)])
            # Mars-Green Outline passend zum System
            Color(0, 1, 0, 0.4)
            self.outline = Line(width=1.2)

        self.panel.bind(pos=self._u, size=self._u)

        # --- UI CONTENT ---
        self.panel.add_widget(Label(
            text="LIGHT CONTROL PRO", 
            bold=True, 
            color=(0, 1, 0, 1),
            font_size=sp_scaled(18),
            size_hint_y=None, height=dp_scaled(30)
        ))

        self.lbl_val = Label(text="0%", font_size=sp_scaled(55), bold=True)
        self.panel.add_widget(self.lbl_val)

        # Slider mit Touch-Sperre Logik
        self.slider = Slider(
            min=0, max=100, step=1,
            size_hint_y=None, height=dp_scaled(45)
        )
        self.slider.bind(value=self._on_slider_change, on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.slider)

        # Grow Stats
        self.stats_box = BoxLayout(orientation="vertical", spacing=dp_scaled(5), size_hint_y=None, height=dp_scaled(60))
        self.lbl_ppfd = Label(text="PPFD: 0 µmol/m²/s", font_size=sp_scaled(15), color=(0.7, 0.7, 1, 1))
        self.lbl_dli = Label(text="DLI: 0.0 mol/m²/d", font_size=sp_scaled(15), color=(0.7, 0.7, 1, 1))
        self.stats_box.add_widget(self.lbl_ppfd)
        self.stats_box.add_widget(self.lbl_dli)
        self.panel.add_widget(self.stats_box)

        # Modi Buttons (Breath / Flicker)
        btn_row = BoxLayout(size_hint_y=None, height=dp_scaled(45), spacing=dp_scaled(10))
        self.btn_man = self._create_styled_btn("MANUAL")
        self.btn_brth = self._create_styled_btn("BREATH")
        self.btn_flck = self._create_styled_btn("FLICKER")
        
        self.btn_man.bind(on_release=lambda *_: self._set_mode("man"))
        self.btn_brth.bind(on_release=lambda *_: self._set_mode("brth"))
        self.btn_flck.bind(on_release=lambda *_: self._set_mode("flicker"))
        
        btn_row.add_widget(self.btn_man); btn_row.add_widget(self.btn_brth); btn_row.add_widget(self.btn_flck)
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
        self.lbl_val.text = f"{int(value)}%"
        # Grow Stats (Berechnung bleibt, aber Logik ist jetzt Fan-Style)
        ppfd = int(value * 12)
        dli = (ppfd * 0.0864) * 0.75
        self.lbl_ppfd.text = f"PPFD: {ppfd} µmol/m²/s"
        self.lbl_dli.text = f"DLI: {dli:.1f} mol/m²/d"

        # EXAKT WIE BEIM FAN:
        now = time.time()
        self._pending_updates["light_pct"] = int(value)
        self._pending_updates["_last_change"] = now  # <--- Der "Macht-Stempel"
        self._last_user_action = now

    def update_ui(self, *_):
        if self._user_active: return 
        
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac: return

        # 1. Daten aus settings_sync.json (Soll-Werte)
        saved_val, saved_mode, last_change = 0, "man", 0
        sync_path = os.path.join(config.DATA, "settings_sync.json")
        
        if os.path.exists(sync_path):
            try:
                with open(sync_path, "r") as f:
                    data = json.load(f).get(mac, {})
                    saved_val = data.get("light_pct", 0)
                    saved_mode = data.get("light_mode", "man")
                    last_change = data.get("_last_change", 0)
            except: pass

        # 2. Das "Macht-Fenster" (Fan-Logik: 8.0 Sekunden)
        is_fresh = (time.time() - last_change) < 8.0

        if not self._pending_updates:
            # Wenn der User NICHT schiebt, Slider auf gespeicherten Wert
            self.slider.value = saved_val
            
            # Button Farben
            self.btn_man.background_color = (0, 1, 0, 0.6) if saved_mode == "man" else (0.2, 0.2, 0.2, 1)
            self.btn_brth.background_color = (0, 1, 0, 0.6) if saved_mode == "brth" else (0.2, 0.2, 0.2, 1)
            self.btn_flck.background_color = (0, 1, 0, 0.6) if saved_mode == "flicker" else (0.2, 0.2, 0.2, 1)

        # Echtzeit-Daten (PPFD/DLI) immer aktuell vom Server zeigen
        server_data = WEB_CLIENT.current_data.get(mac)
        if server_data:
            # Hier zeigen wir die echten Ist-Werte vom Gerät
            actual_pct = server_data.get('light_pct', 0)
            # Optional: Hier könnte man ein "Ist: X%" Label füttern
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

    def _set_mode(self, mode):      
        # HIER WAR DER FEHLER: Es muss light_mode heißen!
        self._pending_updates["light_mode"] = mode 
        self._pending_updates["_last_change"] = time.time()
        self._sync_to_client(0)
        self.update_ui()  # 🔥 direkt Feedback

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
        GLOBAL_STATE.ui_handler.active_light_overlay = None

    def _init_values(self, *_):
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac:
            return
    
        saved_val = 0
        saved_mode = "man"
    
        sync_path = os.path.join(config.DATA, "settings_sync.json")
    
        # 1. settings_sync versuchen
        if os.path.exists(sync_path):
            try:
                with open(sync_path, "r") as f:
                    data = json.load(f).get(mac, {})
                    saved_val = data.get("light_pct", 0)
                    saved_mode = data.get("light_mode", "man")
            except:
                pass
    
        # 2. FALLBACK → LIVE DATEN (KRITISCH)
        if saved_val == 0:
            live_val = WEB_CLIENT.current_data.get(mac, {}).get("light_pct")
            if live_val is not None:
                saved_val = live_val
    
        # 3. SOFORT setzen (kein 0% mehr sichtbar)
        self.slider.value = saved_val
        self.lbl_val.text = f"{int(saved_val)}%"
    
        # Buttons
        self.btn_man.background_color = (0, 1, 0, 0.6) if saved_mode == "man" else (0.2, 0.2, 0.2, 1)
        self.btn_brth.background_color = (0, 1, 0, 0.6) if saved_mode == "brth" else (0.2, 0.2, 0.2, 1)
        self.btn_flck.background_color = (0, 1, 0, 0.6) if saved_mode == "flicker" else (0.2, 0.2, 0.2, 1)