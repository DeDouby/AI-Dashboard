import os
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.graphics import Rectangle, Color, Line
from kivy.clock import Clock
from kivy.metrics import dp, sp
from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.global_state_manager import GLOBAL_STATE
import time
from kivy.uix.textinput import TextInput
from kivy.uix.textinput import TextInput

ASSET_ROOT = os.path.join("dashboard_gui", "assets")


class GlassButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0.1, 0.1, 0.2, 0.4) 
        self.color = (1, 1, 1, 1)
        self.font_size = sp_scaled(14)
        self.bind(pos=self.update_canvas, size=self.update_canvas)

    def update_canvas(self, *args):
        self.canvas.after.clear()
        with self.canvas.after:
            Color(0, 1, 0.4, 0.5) 
            Line(rectangle=(self.x, self.y, self.width, self.height), width=dp(1.1))


class GrowControllerScreen(Screen):
    name = "grow_controller"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        GLOBAL_STATE.ui_handler.attach_screen("grow_controller", self)
        
        self.root = BoxLayout(orientation="vertical")
        self.labels = {}
        self._last_sent_rev = 0
        self._last_send_time = 0
        self._retry_count = 0
        self._max_retries = 5

        # Hintergrund
        with self.root.canvas.before:
            Color(0, 0, 0, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            Color(1, 1, 1, 0.6) 
            self.bg_image = Rectangle(
                source=os.path.join(ASSET_ROOT, "background_grow_controller.png"),
                pos=self.pos, size=self.size
            )
        self.bind(pos=self._update_bg, size=self._update_bg)

        self.header = HeaderBar()
        self.header.set_title("GROW MASTER S3")
        self.header.update_back_button("grow_controller")
        self.root.add_widget(self.header)

        self.scroll = ScrollView(do_scroll_x=False, bar_width=dp(4))
        self.body = GridLayout(cols=2, size_hint_y=None, padding=dp_scaled(15), spacing=dp_scaled(12))
        self.body.bind(minimum_height=self.body.setter('height'))
        self.scroll.add_widget(self.body)
        self.root.add_widget(self.scroll)
        self.add_widget(self.root)

        Clock.schedule_once(self.build_ui, 0.1)
        Clock.schedule_interval(self._check_sync_status, 1.0)

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.bg_image.pos = self.pos
        self.bg_image.size = self.size

    def _add_wide_widget(self, widget):
        container = BoxLayout(size_hint_y=None, height=widget.height)
        widget.size_hint_x = 1  # 🔥 GANZE BREITE nehmen
        container.add_widget(widget)
    
        # 🔥 wichtig: GridLayout erwartet volle Zeile → wir füllen auf
        self.body.add_widget(container)
    
        for _ in range(self.body.cols - 1):
            self.body.add_widget(Widget(size_hint_x=None, width=0))

    def _create_info_card(self, key, label, initial_val="---", unit=""):
        card = BoxLayout(orientation="vertical", size_hint_y=None, height=dp_scaled(65), padding=[dp(12), dp(8)])
        with card.canvas.before:
            Color(0.1, 0.1, 0.15, 0.7)
            card.bg = Rectangle(pos=card.pos, size=card.size)
        card.bind(pos=lambda s, v: setattr(card.bg, 'pos', v), size=lambda s, v: setattr(card.bg, 'size', v))
        
        card.add_widget(Label(text=label.upper(), font_size=sp_scaled(10), color=(0.6, 0.6, 0.7, 1), halign="left", text_size=(dp_scaled(150), None)))
        val_label = Label(text=f"{initial_val} {unit}", font_size=sp_scaled(16), bold=True, color=(1,1,1,1), halign="left", text_size=(dp_scaled(150), None))
        self.labels[key] = val_label
        card.add_widget(val_label)
        return card

    def build_ui(self, *_):
        # 1. Vorbereitung: Body leeren (Scroll-Bereich)
        self.body.clear_widgets()
        self.body.cols = 3
        self.body.padding = dp_scaled(20)
        self.body.spacing = dp_scaled(14)



        # Info Cards
        cards = [
            ("ssid", "Connected To"),    # <--- NEU: WLAN Name
            ("ip", "Node IP"),
            ("rssi", "WiFi Signal", "dBm"),  # <--- NEU: WLAN Signalstärke

            ("uptime", "Uptime"),
            ("rtc_time", "RTC Time"),
            ("rtc_found", "RTC Status"),
            ("boot_cause", "Last Boot"),
            ("fw_ver", "Firmware"),
            ("free_heap", "Free Heap", "bytes"),
            ("max_alloc", "Max Alloc", "bytes"),
            ("rev_grow", "Grow Revision"),
            ("status", "System Status"),
        ]

        for item in cards:
            if len(item) == 3:
                key, label, unit = item
                card = self._create_info_card(key, label, unit=unit)
            else:
                key, label = item
                card = self._create_info_card(key, label)
            self.body.add_widget(card)

        # ====================== ACTIONS (Fest unten/Sticky Footer) ======================
        
        # Falls bereits ein Footer existiert (z.B. bei Rebuild), entfernen
        if hasattr(self, 'footer_layout') and self.footer_layout in self.root.children:
            self.root.remove_widget(self.footer_layout)

        # Der Footer-Container (nimmt volle Breite, feste Höhe)
        self.footer_layout = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp_scaled(100),
            padding=[dp_scaled(20), dp_scaled(10), dp_scaled(20), dp_scaled(20)],
            spacing=dp_scaled(10)
        )

        # Grid für die Buttons (5 Spalten für gleichmäßige Verteilung)
        btn_grid = GridLayout(
            cols=7,
            spacing=dp_scaled(12),
            size_hint_y=1
        )

        buttons = [
            ("[font=FA]\uf021[/font]\nSOFT RESET", self.soft_reset),
            ("[font=FA]\uf017[/font]\nSYNC CLOCK", self.sync_time),
            ("[font=FA]\uf1eb[/font]\nSET WIFI", self.open_wifi_settings), # 🔥 DER NEUE BUTTON
            #("[font=FA]\uf019[/font]\nOTA UPDATE", self.firmware_update),
            ("[font=FA]\uf0c8[/font]\nTEST REV", self.test_rev),
                # 🔥 NEU:
            ("AP MODE", self.set_ap_mode),
            ("ROUTER MODE", self.set_sta_mode),
        ]

        for text, callback in buttons:
            btn = GlassButton(
                text=text, 
                markup=True, 
                on_release=callback,
                halign="center" # Text zentrieren, falls er umbricht
            )
            btn_grid.add_widget(btn)

        # Factory Reset (extra Button am Ende der 5er Reihe)
        f_reset = GlassButton(
            text="[font=FA]\uf1f8[/font]\nFACTORY",
            markup=True,
            on_release=self.factory_reset,
            halign="center"
        )
        f_reset.color = (1, 0.25, 0.25, 1)
        btn_grid.add_widget(f_reset)

        self.footer_layout.add_widget(btn_grid)

        # WICHTIG: Den Footer zum Haupt-Layout hinzufügen
        # Da self.root ein vertikales BoxLayout ist, landet er unter dem ScrollView
        self.root.add_widget(self.footer_layout)
    # ====================== COMMAND SENDEN (wie im Circulation Fan) ======================

# Innerhalb der GrowControllerScreen Klasse:
# ====================== HELPER: SEND COMMAND ======================
    def _send_command(self, command_name):
        """
        Interne Hilfsfunktion, um Standard-Commands (Reset, Sync, etc.)
        an die Engine zu schicken und die Revision zu verwalten.
        """
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac:
            print("[GrowController] Fehler: Keine MAC-Adresse gefunden!")
            return

        # Wir nutzen die Engine, die automatisch rev_grow hochzählt
        new_rev = GLOBAL_STATE.send_overlay_command(
            "grow_controller",
            command=command_name
        )

        if new_rev:
            self._last_sent_rev = new_rev
            self._last_send_time = time.time()
            self._retry_count = 0
            print(f"[GrowController] Command '{command_name}' gesendet. Neue Ziel-Rev: {new_rev}")
    def open_wifi_settings(self, *_):
        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
        
        content.add_widget(Label(text="WLAN KONFIGURATION", bold=True, size_hint_y=None, height=dp(30)))

        # SSID Input - 'placeholder' wurde durch 'hint_text' ersetzt
        self.ssid_input = TextInput(
            text=self.labels["ssid"].text if self.labels["ssid"].text != "---" else "",
            hint_text="SSID (Netzwerk Name)", 
            multiline=False, 
            size_hint_y=None, 
            height=dp(45),
            background_color=(0.15, 0.15, 0.15, 1), 
            foreground_color=(1, 1, 1, 1)
        )
        
        # Passwort Input - 'placeholder' wurde durch 'hint_text' ersetzt
        self.pw_input = TextInput(
            hint_text="Passwort eingeben", 
            password=True, 
            multiline=False, 
            size_hint_y=None, 
            height=dp(45),
            background_color=(0.15, 0.15, 0.15, 1), 
            foreground_color=(1, 1, 1, 1)
        )
        
        content.add_widget(Label(text="Netzwerk Name (SSID):", halign="left", size_hint_y=None, height=dp(20)))
        content.add_widget(self.ssid_input)
        content.add_widget(Label(text="Passwort:", halign="left", size_hint_y=None, height=dp(20)))
        content.add_widget(self.pw_input)
        
        btn_box = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10), padding=[0, dp(10), 0, 0])
        save_btn = GlassButton(text="DATEN SENDEN & REBOOT", color=(0.2, 1, 0.4, 1))
        save_btn.bind(on_release=lambda x: self._apply_wifi_settings(popup))
        
        btn_box.add_widget(save_btn)
        content.add_widget(btn_box)
        
        popup = Popup(title="WiFi Setup", content=content, size_hint=(0.8, 0.5))
        popup.open()

    def _apply_wifi_settings(self, popup):
        # Sende Befehl über die Engine
        new_rev = GLOBAL_STATE.send_overlay_command(
            "grow_controller",
            wifi_ssid=self.ssid_input.text,
            wifi_pw=self.pw_input.text,
            wifi_mode=1 # Schaltet in den Router-Modus (STA)
        )
        
        if new_rev:
            self._last_sent_rev = new_rev
            self._last_send_time = time.time()
            popup.dismiss()

    # ====================== BUTTONS ======================
    def test_rev(self, *_):
        self._send_command("test")   # oder "noop" / "ping"
        print("[GrowController] Test-Command gesendet (sollte Rev hochzählen)")
    
    def soft_reset(self, *_):
        self._send_command("soft_reset")

    def sync_time(self, *_):
        self._send_command("sync_time")

    def firmware_update(self, *_):
        self._send_command("ota_start")

    def factory_reset(self, *_):
        content = BoxLayout(orientation='vertical', padding=20, spacing=15)
        content.add_widget(Label(text="Wirklich FACTORY RESET ausführen?\n\n"
                                     "Alle Einstellungen gehen verloren!", 
                               color=(1, 0.3, 0.3, 1), halign="center"))
        
        btn_box = BoxLayout(size_hint_y=None, height=dp(50), spacing=15)
        yes = GlassButton(text="JA, JETZT ZURÜCKSETZEN", color=(1, 0.2, 0.2, 1))
        no = GlassButton(text="ABBRECHEN")
        
        yes.bind(on_release=lambda x: (self._send_command("factory_reset"), popup.dismiss()))
        no.bind(on_release=lambda x: popup.dismiss())
        
        btn_box.add_widget(yes)
        btn_box.add_widget(no)
        content.add_widget(btn_box)
        
        popup = Popup(title="⚠️ FACTORY RESET", content=content, size_hint=(0.8, 0.45))
        popup.open()

    # ====================== SYNC STATUS & RETRY ======================
    def _check_sync_status(self, dt):
        data = GLOBAL_STATE.overlay_engine.get_buffer_data(GLOBAL_STATE.get_active_device_id())
        if not data:
            return

        server_rev = int(data.get("rev_grow", 0))
        last_sent = getattr(self, '_last_sent_rev', 0)

        if last_sent > server_rev and (time.time() - self._last_send_time > 3.0):
            if self._retry_count < self._max_retries:
                self._retry_count += 1
                print(f"[GrowController] Retry command (Rev {last_sent})")
                # Hier könntest du den letzten Command erneut senden, wenn du ihn speicherst



    def set_ap_mode(self, *_):
        self._send_wifi_mode(0)   # 0 = AP
    
    def set_sta_mode(self, *_):
        self._send_wifi_mode(1)   # 1 = Router
    
    def _send_wifi_mode(self, mode):
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac:
            print("[GrowController] Kein Device!")
            return
    
        new_rev = GLOBAL_STATE.send_overlay_command(
            "grow_controller",
            wifi_mode=mode   # 🔥 DIREKT
        )
    
        if new_rev:
            self._last_sent_rev = new_rev
            self._last_send_time = time.time()
            self._retry_count = 0
            print(f"[GrowController] WIFI MODE -> {mode} (rev={new_rev})")
    # ====================== LIVE UPDATE (Decoder Pipeline) ======================
    def update_from_global(self, data):
        if not data: 
            return
        
        self.header.update_from_global(data)
        web = data.get("webserver", {})

        # Uptime
        esp_s = web.get("uptime_esp_s")
        if esp_s is not None:
            s = int(esp_s)
            h = s // 3600
            m = (s % 3600) // 60
            sec = s % 60
            self.labels["uptime"].text = f"{h:02d}:{m:02d}:{sec:02d}" if h < 24 else f"{h//24}d {h%24:02d}:{m:02d}:{sec:02d}"

        # Revision
        if "rev_grow" in web:
            self.labels["rev_grow"].text = f"REV-{web['rev_grow']}"

        # Heap
        if "free_heap" in web:
            heap = int(web["free_heap"])
            self.labels["free_heap"].text = f"{heap:,}".replace(",", ".")
            color = (1,0.2,0.2,1) if heap < 90000 else (1,0.65,0,1) if heap < 130000 else (0.2,1,0.2,1)
            self.labels["free_heap"].color = color

        if "max_alloc" in web:
            self.labels["max_alloc"].text = f"{int(web['max_alloc']):,}".replace(",", ".")
        
        if "wifi_mode" in web:
            mode = web["wifi_mode"]
            if "status" in self.labels:
                if mode == 0:
                    self.labels["status"].text = "AP MODE"
                else:
                    self.labels["status"].text = "ROUTER MODE"        
        # Status sauber anzeigen
        if "status" in web:
            status = web["status"]
            self.labels["status"].text = status.upper()
            if status == "active":
                self.labels["status"].color = (0.2, 1, 0.2, 1)
            else:
                self.labels["status"].color = (1, 0.7, 0.2, 1)

        # Optional: alive anzeigen
        if "alive" in data:
            self.labels.setdefault("alive", None)  # falls du noch ein Label dafür willst
        
        
        # Andere Werte
    # Alle Standard-Werte inkl. SSID und RSSI updaten
        for key in ["ip", "ssid", "rssi", "boot_cause", "fw_ver", "rtc_time"]:
            if key in web and key in self.labels:
                self.labels[key].text = str(web[key])
                
                # Optional: Signalstärke farblich markieren
                if key == "rssi" and "dBm" in str(web[key]):
                    try:
                        val = int(web[key].replace(" dBm", ""))
                        if val > -60: self.labels[key].color = (0.2, 1, 0.2, 1) # Super
                        elif val > -80: self.labels[key].color = (1, 0.7, 0.2, 1) # Okay
                        else: self.labels[key].color = (1, 0.2, 0.2, 1) # Kritisch
                    except: pass

        if "rtc_found" in web:
            found = web["rtc_found"]
            self.labels["rtc_found"].text = "OK" if found else "NOT FOUND"
            self.labels["rtc_found"].color = (0.2,1,0.2,1) if found else (1,0.3,0.2,1)