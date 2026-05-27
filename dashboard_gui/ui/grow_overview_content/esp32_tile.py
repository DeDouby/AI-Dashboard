import os

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle, Line

from dashboard_gui.ui.scaling_utils import sp_scaled, dp_scaled


ASSET_ROOT = os.path.join("dashboard_gui", "assets")
ESP32_PIC = os.path.join(ASSET_ROOT, "hardware_pics", "esp32_board.png")


class ESP32Tile(BoxLayout):

    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)

        self.padding = dp_scaled(10)
        self.spacing = dp_scaled(8)

        # ==================== CONTENT CONTAINER ====================
        self.content_container = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            spacing=dp_scaled(12),
            height=dp_scaled(500)  # genug Platz für Bild + Werte
        )

        # ---------------- VALUE BOX TOP ----------------
        self.value_box_top = self._create_value_box()
        self.content_container.add_widget(self.value_box_top)

        # ---------------- IMAGE ----------------
        self.device_image = Image(
            source=ESP32_PIC,
            size_hint=(None, 1),
            width=dp_scaled(400)
        )
        self.content_container.add_widget(self.device_image)

        # ---------------- VALUE BOX BOTTOM ----------------
        self.value_box_bottom = self._create_value_box()
        self.content_container.add_widget(self.value_box_bottom)

        self.add_widget(self.content_container)

        # Labels
        self.labels = {}
        self._create_labels()

    def _create_value_box(self):
        box = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            padding=[dp_scaled(14), dp_scaled(12)],
            spacing=dp_scaled(4),
            height=dp_scaled(60)          # etwas höher für mehr Inhalt
        )

        # Canvas erstellen
        with box.canvas.before:
            Color(0, 0, 0, 0.65)
            bg = RoundedRectangle(pos=box.pos, size=box.size, radius=[dp_scaled(14)])

            Color(0.2, 1, 0.8, 0.15)
            glow = Line(width=5, rounded_rectangle=(0, 0, 0, 0, dp_scaled(14)))

            Color(0.2, 1, 0.8, 0.6)
            border = Line(width=1.3, rounded_rectangle=(0, 0, 0, 0, dp_scaled(14)))

        # Referenzen speichern
        box.bg = bg
        box.glow = glow
        box.border = border

        # Bind für Update
        box.bind(pos=self._update_canvas, size=self._update_canvas)

        return box

    def _create_labels(self):
        # === TOP BOX ===
        top_cards = [
            ("status", "System Status"),
        ]

        for item in top_cards:
            self._add_label(self.value_box_top, item)

        # === BOTTOM BOX ===
        bottom_cards = [
            ("uptime", "Uptime"),
#            ("rtc_found", "RTC Status"),
#            ("free_heap", "Free Heap", " Bytes"),
#            ("max_alloc", "Max Alloc", " Bytes"),
#            ("fw_ver", "Firmware"),
#            ("rev_grow", "Revision"),
#            ("boot_cause", "Boot Cause"),
#            ("wifi_mode", "WiFi Mode"),
        ]

        for item in bottom_cards:
            self._add_label(self.value_box_bottom, item)

    def _add_label(self, parent, item):
        key = item[0]
        title = item[1]
        unit = item[2] if len(item) > 2 else ""

        lbl = Label(
            text=f"{title}: -",
            font_size=sp_scaled(19),
            halign="left",
            valign="middle",
            size_hint=(1, None),
            height=dp_scaled(28)
        )
        lbl.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))

        self.labels[key] = (lbl, unit)
        parent.add_widget(lbl)

    # ==================== CANVAS UPDATE ====================
    def _update_canvas(self, obj, *args):
        x, y = obj.pos
        w, h = obj.size
        r = dp_scaled(14)

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

        web = data.get("webserver", data) if isinstance(data, dict) else {}

        def set_label(key, text, color=None):
            if key not in self.labels:
                return
            lbl, _ = self.labels[key]
            lbl.text = text
            if color:
                lbl.color = color

        # ===================== TOP BOX =====================
        if "ssid" in web:
            set_label("ssid", f"Connected To: {web['ssid']}")

        if "ip" in web:
            set_label("ip", f"Node IP: {web['ip']}")

        if "rssi" in web:
            rssi = web["rssi"]
            set_label("rssi", f"RSSI: {rssi} dBm")
            try:
                val = int(str(rssi).replace(" dBm", ""))
                if val > -60:
                    self.labels["rssi"][0].color = (0.2, 1, 0.2, 1)
                elif val > -80:
                    self.labels["rssi"][0].color = (1, 0.8, 0.2, 1)
                else:
                    self.labels["rssi"][0].color = (1, 0.2, 0.2, 1)
            except:
                pass

        if "status" in web:
            status = str(web["status"]).upper()
            color = (0.2, 1, 0.2, 1) if status in ("ACTIVE", "OK") else (1, 0.7, 0.2, 1)
            set_label("status", f"System Status: {status}", color)

        # ===================== BOTTOM BOX =====================
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

        if "rtc_found" in web:
            found = web["rtc_found"]
            text = "RTC Status: OK" if found else "RTC Status: NOT FOUND"
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

        if "fw_ver" in web:
            set_label("fw_ver", f"Firmware: {web['fw_ver']}")

        if "rev_grow" in web:
            set_label("rev_grow", f"Revision: REV-{web['rev_grow']}")

        if "boot_cause" in web:
            set_label("boot_cause", f"Boot Cause: {web['boot_cause']}")

        if "wifi_mode" in web:
            mode = "AP MODE" if web["wifi_mode"] == 0 else "ROUTER MODE"
            set_label("wifi_mode", f"WiFi Mode: {mode}")