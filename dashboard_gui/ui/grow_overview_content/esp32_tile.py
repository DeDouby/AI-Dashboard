import os
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle, Line

from dashboard_gui.ui.scaling_utils import sp_scaled, dp_scaled

ASSET_ROOT = os.path.join("dashboard_gui", "assets")
ESP32_PIC = os.path.join(ASSET_ROOT, "hardware_pics", "esp32_board.png")

VALUE_BOX_WIDTH = dp_scaled(220)

TOP_BOX_HEIGHT = dp_scaled(180)
BOTTOM_BOX_HEIGHT = dp_scaled(310)
class ESP32Tile(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=dp_scaled(12), padding=dp_scaled(10), **kwargs)
        # ==================== BOX SIZES ====================

        self.top_box_height = dp_scaled(180)
        self.top_box_width = dp_scaled(650)

        self.bottom_box_height = dp_scaled(310)
        self.bottom_box_width = dp_scaled(650)
        # ==================== MAIN CONTAINER ====================
        self.content_container = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            spacing=dp_scaled(15),
            height=dp_scaled(1300)
        )

        # ---------------- TOP BOX (wichtigste Infos) ----------------
        self.top_box = self._create_value_box(height=dp_scaled(180), title="System Status")
        self.content_container.add_widget(self.top_box)

        # ---------------- IMAGE ----------------
        self.device_image = Image(
            source=ESP32_PIC,
            size_hint=(1, None),
            height=dp_scaled(520),
            allow_stretch=True,
            keep_ratio=True
        )
        self.content_container.add_widget(self.device_image)

        # ---------------- BOTTOM BOX (alle anderen Infos) ----------------
        self.bottom_box = self._create_value_box(height=dp_scaled(310), title="Details")
        self.content_container.add_widget(self.bottom_box)

        self.add_widget(self.content_container)

        # Labels verwalten
        self.labels = {}
        self._create_labels()

    def _create_value_box(self, height, title=""):
        box = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            height=height,
            padding=dp_scaled(14),
            spacing=dp_scaled(6)
        )

        # Optionaler Titel
        if title:
            title_label = Label(
                text=title,
                font_size=sp_scaled(18),
                bold=True,
                color=(0.2, 1, 0.8, 1),
                size_hint_y=None,
                height=dp_scaled(28),
                halign="left"
            )
            box.add_widget(title_label)

        # Canvas (schöner Rahmen + Glow)
        with box.canvas.before:
            Color(0, 0, 0, 0.7)
            box.bg = RoundedRectangle(pos=box.pos, size=box.size, radius=[dp_scaled(16)])

            Color(0.2, 1, 0.8, 0.18)
            box.glow = Line(width=6, rounded_rectangle=(0, 0, 0, 0, dp_scaled(16)))

            Color(0.2, 1, 0.8, 0.75)
            box.border = Line(width=1.5, rounded_rectangle=(0, 0, 0, 0, dp_scaled(16)))

        box.bind(pos=self._update_canvas, size=self._update_canvas)
        return box

    def _create_labels(self):
        # === TOP BOX - WICHTIGSTE INFOS ===
        top_items = [
            ("status", "System Status"),
            ("ssid", "Connected To"),
            ("ip", "IP Address"),
            ("rssi", "Signal Strength"),
        ]

        for key, title in top_items:
            self._add_label(self.top_box, key, title)

        # === BOTTOM BOX - DETAILINFOS ===
        bottom_items = [
            ("uptime", "Uptime"),
            ("fw_ver", "Firmware"),
            ("rev_grow", "Revision"),
            ("boot_cause", "Boot Cause"),
            ("wifi_mode", "WiFi Mode"),
            ("rtc_found", "RTC"),
            ("free_heap", "Free Heap"),
            ("max_alloc", "Max Alloc"),
        ]

        for key, title in bottom_items:
            self._add_label(self.bottom_box, key, title)

    def _add_label(self, parent, key, title):
        lbl = Label(
            text=f"{title}: -",
            font_size=sp_scaled(17.5),
            halign="left",
            valign="middle",
            size_hint=(1, None),
            height=dp_scaled(26)
        )
        lbl.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))

        self.labels[key] = lbl
        parent.add_widget(lbl)

    # ==================== CANVAS UPDATE ====================
    def _update_canvas(self, obj, *args):
        x, y = obj.pos
        w, h = obj.size
        r = dp_scaled(16)

        if hasattr(obj, 'bg'):
            obj.bg.pos = (x, y)
            obj.bg.size = (w, h)

        rect = (x, y, w, h, r)
        if hasattr(obj, 'glow'):
            obj.glow.rounded_rectangle = rect
        if hasattr(obj, 'border'):
            obj.border.rounded_rectangle = rect

    # ==================== DATA UPDATE ====================
    def update_values(self, data):
        if not data:
            return

        web = data.get("webserver", data)

        def set_label(key, text, color=None):
            if key not in self.labels:
                return
            lbl = self.labels[key]
            lbl.text = text
            if color:
                lbl.color = color

        # ==================== TOP BOX ====================
        if "status" in web:
            status = str(web["status"]).upper()
            color = (0.2, 1, 0.2, 1) if status in ("ACTIVE", "OK") else (1, 0.7, 0.2, 1)
            set_label("status", f"System Status: {status}", color)

        if "ssid" in web:
            set_label("ssid", f"Connected To: {web['ssid']}")

        if "ip" in web:
            set_label("ip", f"IP: {web['ip']}")

        if "rssi" in web:
            rssi = web["rssi"]
            try:
                val = int(str(rssi).replace(" dBm", ""))
                if val > -60:
                    color = (0.2, 1, 0.2, 1)
                elif val > -80:
                    color = (1, 0.85, 0.2, 1)
                else:
                    color = (1, 0.3, 0.2, 1)
                set_label("rssi", f"RSSI: {rssi} dBm", color)
            except:
                set_label("rssi", f"RSSI: {rssi}")

        # ==================== BOTTOM BOX ====================
        if "uptime_esp_s" in web:
            try:
                s = int(web["uptime_esp_s"])
                h = s // 3600
                m = (s % 3600) // 60
                sec = s % 60
                uptime_str = f"{h:02d}:{m:02d}:{sec:02d}" if h < 24 else f"{h//24}d {h%24:02d}:{m:02d}:{sec:02d}"
                set_label("uptime", f"Uptime: {uptime_str}")
            except:
                pass

        if "fw_ver" in web:
            set_label("fw_ver", f"Firmware: {web['fw_ver']}")

        if "rev_grow" in web:
            set_label("rev_grow", f"Revision: REV-{web['rev_grow']}")

        if "boot_cause" in web:
            set_label("boot_cause", f"Boot Cause: {web['boot_cause']}")

        if "wifi_mode" in web:
            mode = "AP Mode" if web["wifi_mode"] == 0 else "Router Mode"
            set_label("wifi_mode", f"WiFi Mode: {mode}")

        if "rtc_found" in web:
            found = web["rtc_found"]
            text = "RTC: OK" if found else "RTC: NOT FOUND"
            color = (0.2, 1, 0.2, 1) if found else (1, 0.3, 0.2, 1)
            set_label("rtc_found", text, color)

        if "free_heap" in web:
            try:
                heap = int(web["free_heap"])
                color = (1,0.2,0.2,1) if heap < 90000 else (1,0.65,0,1) if heap < 130000 else (0.2,1,0.2,1)
                set_label("free_heap", f"Free Heap: {heap:,}".replace(",", "."), color)
            except:
                pass

        if "max_alloc" in web:
            set_label("max_alloc", f"Max Alloc: {int(web['max_alloc']):,}".replace(",", "."))


    def on_touch_down(self, touch):
        # 1. Collision check: Nur reagieren, wenn innerhalb des Tiles geklickt wurde
        if self.collide_point(*touch.pos):
            from dashboard_gui.ui.common.signal_inspector import SignalInspector
            from kivy.app import App
            
            # 2. Prüfen, ob bereits ein Inspector offen ist (analog zu deinem Header-Pattern)
            # Falls du eine globale Instanz-Verwaltung hast, nutze diese hier.
            # Andernfalls: Schließe einen existierenden, falls die Referenz in der App liegt
            app = App.get_running_app()
            
            # Öffne den Inspector
            # Übergib 'self' als parent_header, damit er auf die Daten zugreifen kann
            inspector = SignalInspector(parent_header=self)
            
            # Zum aktuellen Screen hinzufügen
            screen = app.root.current_screen
            screen.add_widget(inspector)
            
            return True  # Event wurde verarbeitet
            
        return super().on_touch_down(touch)