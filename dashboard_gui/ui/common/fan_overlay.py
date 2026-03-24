import threading
import time
import requests
import json

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.clock import Clock

from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled

class FanOverlay(FloatLayout):
    def __init__(self, parent_header, **kwargs):
        super().__init__(**kwargs)
        self.parent_header = parent_header
        
        # NEU: Der Zettelkasten für Änderungen (Buffer)
        self._pending_updates = {} 
        self._last_payload = {}    
        
        # TAKTGEBER 1: Schaut alle 0,3s ob wir Daten senden müssen
        self._sync_event = Clock.schedule_interval(self._sync_to_device, 1.3)
        
        # TAKTGEBER 2: Holt alle 0,5s den aktuellen Status vom ESP (RPM etc.)
        self._update_event = Clock.schedule_interval(self.update_ui, 1.5)

        # --- UI AUFBAU (BACKDROP) ---
        bg = Button(background_color=(0, 0, 0, 0.25))
        bg.bind(on_release=lambda *_: self.close())
        self.add_widget(bg)

        # --- UI AUFBAU (PANEL) ---
        self.panel = BoxLayout(
            orientation="vertical",
            padding=dp_scaled(15),
            spacing=dp_scaled(10),
            size_hint=(None, None),
            size=(dp_scaled(320), dp_scaled(260)),
            pos_hint={"right": 0.98, "top": 0.98}
        )

        with self.panel.canvas.before:
            Color(0, 0, 0, 0.65)
            self.bg_rect = RoundedRectangle(radius=[dp_scaled(20)])
            Color(0, 1, 0, 0.4)
            self.outline = Line(width=1.2)

        self.panel.bind(pos=self._update_canvas, size=self._update_canvas)

        self.lbl = Label(
            text="Lade Daten...",
            font_size=sp_scaled(14),
            halign="left",
            valign="top"
        )
        self.lbl.bind(size=lambda *_: setattr(self.lbl, "text_size", self.lbl.size))

        # --- SLIDER ---
        self.slider = Slider(min=0, max=100, value=0, step=1)
        self._user_active = False # Merkt sich, ob der Finger gerade drauf ist
        
        self.slider.bind(on_touch_down=self._touch_down)
        self.slider.bind(on_touch_up=self._touch_up)
        self.slider.bind(value=self._on_slider_change)

        # --- BUTTONS ---
        btn_row = BoxLayout(size_hint_y=None, height=dp_scaled(40), spacing=dp_scaled(5))
        self.btn_man = Button(text="MAN")
        self.btn_nat = Button(text="NAT")
        self.btn_chao = Button(text="CHAO")

        self.btn_man.bind(on_release=lambda *_: self._set_mode("man"))
        self.btn_nat.bind(on_release=lambda *_: self._set_mode("nat"))
        self.btn_chao.bind(on_release=lambda *_: self._set_mode("chao"))

        btn_row.add_widget(self.btn_man)
        btn_row.add_widget(self.btn_nat)
        btn_row.add_widget(self.btn_chao)

        self.panel.add_widget(self.lbl)
        self.panel.add_widget(self.slider)
        self.panel.add_widget(btn_row)
        self.add_widget(self.panel)

    # -----------------------
    # LOGIK: DATEN SENDEN (JSON)
    # -----------------------
# -----------------------
    # LOGIK: DATEN SENDEN (JSON)
    # -----------------------
    def _sync_to_device(self, dt):
        """ Schickt das Paket nur ab, wenn der Zettelkasten NICHT leer ist. """
        # Wenn nichts auf dem Zettel steht ODER wir schon genau das gesendet haben -> Nichts tun
        if not self._pending_updates or self._pending_updates == self._last_payload:
            return
            
        payload = self._pending_updates.copy()
        self._last_payload = payload.copy()
        
        # WICHTIG: Wir starten den Versand leise im Hintergrund
        threading.Thread(target=self._send_json_request, args=(payload,), daemon=True).start()

    def _send_json_request(self, payload):
        try:
            ip = GLOBAL_STATE.get_active_device_ip()
            if not ip: return
            
            # Timeout auf 2.0s hoch, damit Android nicht sofort Panik kriegt
            r = requests.post(f"http://{ip}/control", json=payload, timeout=2.0)
            
            # ERST WENN DER ESP "OK" SAGT:
            if r.status_code == 200:
                # Wir leeren den Zettelkasten erst bei Erfolg!
                # Das bedeutet: Solange _pending_updates voll ist, blockieren wir den Rücksprung.
                self._pending_updates.clear()
        except:
            # Bei Fehler: Wir machen nichts. Der Zettel bleibt voll, 
            # der nächste Takt probiert es einfach nochmal.
            pass

    # -----------------------
    # LOGIK: WERTE ÄNDERN (OPTIMISTISCH)
    # -----------------------
    def _on_slider_change(self, slider, value):
        if not self._user_active:
            return
        # Wir notieren den Wunsch-Wert
        self._pending_updates["fan_pct"] = int(value)
        # Das UI zeigt SOFORT den Zielwert an, egal was der ESP sagt
        self.lbl.text = f"Ziel: {int(value)}%"



    def _set_mode(self, mode):
        # Modus für den Versand vormerken
        self._pending_updates["mode"] = mode
        # Sofort-Feedback im UI (Buttons kurz ausgrauen, bis Bestätigung kommt)
        self.btn_man.background_color = (0.5, 0.5, 0.5, 1)
        self.btn_nat.background_color = (0.5, 0.5, 0.5, 1)
        self.btn_chao.background_color = (0.5, 0.5, 0.5, 1)
    # -----------------------
    # UI UPDATES & TOUCH
    # -----------------------
    def update_ui(self, *_):
        """ Holt RPM und Modus vom ESP und färbt die Buttons ein. """
        try:
            ip = GLOBAL_STATE.get_active_device_ip()
            if not ip: return

            r = requests.get(f"http://{ip}/data", timeout=0.8)
            if r.status_code == 200:
                j = r.json()
                rpm = j.get("rpm", 0)
                pct = j.get("fan_pct", 0)
                mode = j.get("mode", "man") # Den neuen Modus auslesen
                
                GLOBAL_STATE.fan_rpm = rpm
                
                # Slider & Label Update (nur wenn User nicht aktiv)
                if not self._user_active and not self._pending_updates:
                    self.slider.value = pct
                    self.lbl.text = f"RPM: {rpm}\nStatus: {pct}%"
                    
                    # BUTTON FARBEN AKTUALISIEREN
                    # Grün = (0, 1, 0, 0.4), Standard = (1, 1, 1, 1)
                    self.btn_man.background_color = (0, 1, 0, 0.6) if mode == "man" else (1, 1, 1, 1)
                    self.btn_nat.background_color = (0, 1, 0, 0.6) if mode == "nat" else (1, 1, 1, 1)
                    self.btn_chao.background_color = (0, 1, 0, 0.6) if mode == "chao" else (1, 1, 1, 1)
                else:
                    self.lbl.text = f"RPM: {rpm}\nSynchronisiere..."
        except:
            pass


    def _touch_down(self, slider, touch):
        if slider.collide_point(*touch.pos):
            self._user_active = True

    def _touch_up(self, slider, touch):
        if slider.collide_point(*touch.pos):
            self._user_active = False
            # Beim Loslassen erzwingen wir eine sofortige Notiz im Zettelkasten
            self._pending_updates["fan_pct"] = int(slider.value)

    def _update_canvas(self, obj, *_):
        self.bg_rect.pos = obj.pos
        self.bg_rect.size = obj.size
        self.outline.rounded_rectangle = (obj.x, obj.y, obj.width, obj.height, dp_scaled(20))

    def close(self):
        # Wichtig: Alle Taktgeber stoppen!
        if self._update_event: self._update_event.cancel()
        if self._sync_event: self._sync_event.cancel()
        
        ui = GLOBAL_STATE.ui_handler
        if getattr(ui, "active_fan_overlay", None) == self:
            ui.active_fan_overlay = None
        if self.parent:
            self.parent.remove_widget(self)