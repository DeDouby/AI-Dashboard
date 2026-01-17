# -------------------------------------------------------
# header_online.py — FINAL FIXED MINIMAL PATCH
# -------------------------------------------------------

import time
import os

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.graphics import Color, Rectangle, Ellipse
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from kivy.app import App

from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.ui.common.window_picker import WindowPicker
# -------------------------------------------------------
# IconLabel
# -------------------------------------------------------
class IconLabel(Label):
    def __init__(self, **kw):
        kw.setdefault("font_name", "FA")
        kw.setdefault("font_size", sp_scaled(22))
        kw.setdefault("halign", "center")
        kw.setdefault("valign", "middle")
        super().__init__(**kw)
        self.bind(size=lambda *_: self.texture_update())


# -------------------------------------------------------
# Signal Bars (PNG Version)
# -------------------------------------------------------
class SignalBars(BoxLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.size_hint = kw.get("size_hint", (None, 1))
        self.width = dp_scaled(40)

        # Bild-Widget vorbereiten
        self.img = Image(
            allow_stretch=True,
            keep_ratio=True,
        )
        self.add_widget(self.img)

        # absoluter Pfad zu /dashboard_gui/assets/icons/signal
        self._icon_dir = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "assets", "icons", "signal"
        )

        # Default: kein Signal
        self.set_rssi(None)

    def _pick_icon(self, level):
        """level = 0..5"""
        fn = f"signal{level}.png"
        p = os.path.join(self._icon_dir, fn)
        return p if os.path.exists(p) else ""

    def set_rssi(self, rssi):
        """RSSI → 0..5 Balken"""
        try:
            rssi = float(rssi)
        except:
            level = 0
            self.img.source = self._pick_icon(level)
            return

        # Abstufungen (anpassbar)
        if rssi >= -55:
            level = 5
        elif rssi >= -65:
            level = 4
        elif rssi >= -75:
            level = 3
        elif rssi >= -85:
            level = 2
        elif rssi >= -95:
            level = 1
        else:
            level = 0

        self.img.source = self._pick_icon(level)
        self.img.reload()


# -------------------------------------------------------
# External Sensor
# -------------------------------------------------------
class ExternalIcon(BoxLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.orientation = "vertical"
        self.spacing = dp_scaled(0)

        self.icon = IconLabel(font_size=sp_scaled(20))
        self.text_label = Label(font_size=sp_scaled(14), color=(0.8, 0.8, 0.8, 1))

        self.add_widget(self.icon)
        self.add_widget(self.text_label)

        # Standardzustand
        self.set_external(False)

    def set_external(self, present):
        """Einfacher Setter (Boolean) für die UI-Anzeige."""
        if present:
            self.icon.text = "\uf2c7"
            self.icon.color = (0.3, 1, 0.3, 1)
            self.text_label.text = "EXT"
            self.text_label.color = (0.6, 1, 0.6, 1)
        else:
            self.icon.text = "\uf059"
            self.icon.color = (0.7, 0.7, 0.7, 1)
            self.text_label.text = "none"
            self.text_label.color = (0.7, 0.7, 0.7, 1)

# -------------------------------------------------------
# LED Circle – MODERN UI (NO LOGIC CHANGE)
# -------------------------------------------------------
class LEDCircle(Widget):
    def __init__(self, **kw):
        super().__init__(**kw)

        self._pulse_event = None
        self._base_status = "offline"

        with self.canvas:
            # --- Outer Glow ---
            self.glow_color = Color(0, 1, 0, 0.25)
            self.glow = Ellipse()

            # --- Ring ---
            self.ring_color = Color(0, 1, 0, 0.9)
            self.ring = Ellipse()

            # --- Core ---
            self.core_color = Color(0, 1, 0, 1)
            self.core = Ellipse()

        self.bind(pos=self._u, size=self._u)
        self._u()

    def _u(self, *_):
        size = dp_scaled(20)
        glow = size * 1.6
        ring = size * 1.15

        cx = self.x + self.width / 2
        cy = self.y + self.height / 2

        self.glow.size = (glow, glow)
        self.glow.pos = (cx - glow / 2, cy - glow / 2)

        self.ring.size = (ring, ring)
        self.ring.pos = (cx - ring / 2, cy - ring / 2)

        self.core.size = (size, size)
        self.core.pos = (cx - size / 2, cy - size / 2)

    # -------------------------------
    # LOGIC – UNCHANGED
    # -------------------------------
    def set_state(self, alive, status):
        base = "stale" if status == "flow" else status
        self._base_status = base

        if base in ("offline", "error") and self._pulse_event:
            self._pulse_event.cancel()
            self._pulse_event = None

        if not self._pulse_event:
            self._apply(base)

        if status == "flow":
            self._pulse()

    def _apply(self, s):
        if s in ("nodata", "stale"):
            self._set_color(1, 0.8, 0); return
        if s == "error":
            self._set_color(1, 0, 0); return
        if s == "offline":
            self._set_color(0.9, 0.1, 0.1); return

        self._set_color(0.5, 0.5, 0.5)

    def _set_color(self, r, g, b):
        self.core_color.rgba = (r, g, b, 1)
        self.ring_color.rgba = (r * 0.8, g * 0.8, b * 0.8, 0.9)
        self.glow_color.rgba = (r, g, b, 0.25)

    def _pulse(self):
        if self._pulse_event:
            self._pulse_event.cancel()

        self._set_color(0.3, 1, 0.3)
        self.glow_color.a = 0.45

        self._pulse_event = Clock.schedule_once(
            lambda *_: self._end(), 0.20
        )

    def _end(self, *_):
        self._pulse_event = None
        self._apply(self._base_status)


from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.metrics import dp, sp
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
import config

class DevicePickerMenu(FloatLayout):
    def __init__(self, parent_header, device_list, on_select_device, **kw):
        super().__init__(**kw)
        self.parent_header = parent_header

        from dashboard_gui.global_state_manager import GLOBAL_STATE
        self._current_idx = GLOBAL_STATE.active_index

        # -----------------------------
        # 1) Hintergrund Overlay
        # -----------------------------
        bg = Button(
            background_color=(0, 0, 0, 0.15),  # nur 15% Deckkraft
            border=(0,0,0,0)
        )
        bg.bind(on_release=lambda *_: self.close())
        self.add_widget(bg)

        # -----------------------------
        # 2) Panel für Buttons
        # -----------------------------
        num_buttons = len(device_list) + 2   # ADV + GATT
        w = dp_scaled(220)
        h = dp_scaled(40 * num_buttons + 20)

        self.panel = BoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            size=(w, h),
            spacing=dp_scaled(6),
            padding=[dp_scaled(4), dp_scaled(4), dp_scaled(4), dp_scaled(4)],
            pos=(
                parent_header.lbl_dev.to_window(*parent_header.lbl_dev.pos)[0],
                parent_header.lbl_dev.to_window(*parent_header.lbl_dev.pos)[1] - h - dp_scaled(10)
            )
        )
        self.add_widget(self.panel)

        # -----------------------------
        # 3) Devices aus Config
        # -----------------------------
        cfg = config._init()
        devices_cfg = cfg.get("devices", {})

        for idx, mac in enumerate(device_list):
            name = devices_cfg.get(mac, {}).get("name")
            label = name if name else mac

            b = Button(
                text=label,
                font_size=sp_scaled(18),
                background_color=(0.22, 0.25, 0.30, 0.55),  # semi-transparent
                color=(0.95, 0.95, 0.98, 1)
            )
            b.bind(on_release=lambda _, i=idx: (
                on_select_device(i),
                setattr(self, "_current_idx", i),
                self.close()
            ))
            self.panel.add_widget(b)

        # -----------------------------
        # 4) Separator
        # -----------------------------
        sep = Label(text="CHANNEL", font_size=sp_scaled(14), color=(0.8, 0.8, 0.8, 1))
        self.panel.add_widget(sep)

        # -----------------------------
        # 5) Channel Buttons (ADV / GATT)
        # -----------------------------
        # ADV
        b_adv = Button(
            text="ADV channel",
            font_size=sp_scaled(18),
            background_color=(0.20, 0.30, 0.25, 0.55),
            color=(0.95,0.95,0.98,1)
        )
        b_adv.bind(
            on_release=lambda *_: (
                GLOBAL_STATE.set_active_channel("adv"),
                self.close()
            )
        )
        self.panel.add_widget(b_adv)

        # GATT
        b_gatt = Button(
            text="GATT channel",
            font_size=sp_scaled(18),
            background_color=(0.25, 0.20, 0.30, 0.55),
            color=(0.95,0.95,0.98,1)
        )
        def activate_gatt():
            import core
            device_id = device_list[self._current_idx]
            dev_cfg = cfg.get("devices", {}).get(device_id, {})
            bridge_profile = dev_cfg.get("bridge_profile", "")

            if bridge_profile:
                GLOBAL_STATE.write_gatt_bridge_config(device_id)
                core.restart_bridge()

            GLOBAL_STATE.set_active_channel("gatt")
            self.close()

        b_gatt.bind(on_release=lambda *_: activate_gatt())
        self.panel.add_widget(b_gatt)

    # -----------------------------
    # 6) Menü schließen
    # -----------------------------
    def close(self):
        if self.parent:
            self.parent.remove_widget(self)
            if self.parent_header:
                self.parent_header._device_menu = None

# -------------------------------------------------------
# HEADER BAR
# -------------------------------------------------------
class HeaderBar(BoxLayout):
    def __init__(self, **kw):
        super().__init__(**kw)

        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp_scaled(50)
        self.spacing = dp_scaled(10)
        self.padding = [dp_scaled(10), dp_scaled(8)]

        with self.canvas.before:
            Color(0.1, 0.1, 0.15, 0.65)
            self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._u_bg, size=self._u_bg)

        # BACK BUTTON (stabil)
        self.btn_back = Button(
            text="\uf060",   # FontAwesome icon
            font_name="FA",
            size_hint=(None, 1),
            width=dp_scaled(40),
            background_color=(0.22, 0.25, 0.30, 0.9),
            color=(0.95, 0.95, 0.98, 1),
            font_size=sp_scaled(22),
            opacity=0,
            disabled=True,
        )
        self.btn_back.size_hint_x = None
        self.btn_back.bind(on_release=lambda *_: self._go_back())


        # LOGO
        logo = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "Logo.png")
        self.device_icon = Image(source=logo, size_hint=(None, 1))
        self.device_icon.width = dp_scaled(30)

        # TEXT & ICONS
        self.lbl_title = Label(
            text="Mano Verde Panel",
            font_size=sp_scaled(22),
            halign="left",
            size_hint=(0.28, 1)
        )
        
        self.lbl_dev = Button(
            text="---",
            font_size=sp_scaled(20),
            size_hint=(0.20, 1),
            background_color=(0, 0, 0, 0),
            color=(0.95, 0.95, 0.98, 1)
        )
        self.lbl_dev.bind(on_release=lambda *_: self._open_device_menu())
        
        self.signal = SignalBars(size_hint=(0.09, 1))
        self.external = ExternalIcon(size_hint=(0.08, 1))
        self.led = LEDCircle(size_hint=(0.07, 1))

        self.lbl_clock = Label(text="--:--", font_size=sp_scaled(20),
                               size_hint=(0.10, 1))
        Clock.schedule_interval(self._update_clock, 1)


        # MENU BUTTON
        self.btn_menu = Button(
            text="\uf0c9",   # FA "bars"
            font_name="FA",
            size_hint=(0.08, 1),
            background_color=(0.22, 0.25, 0.30, 0.9),
            color=(0.95, 0.95, 0.98, 1),
            font_size=sp_scaled(22)
        )
        self.btn_menu.bind(on_release=lambda *_: self._open_menu())

        # assemble
        self.add_widget(self.device_icon)
        self.add_widget(self.lbl_title)
        self.add_widget(self.lbl_dev)
        self.add_widget(self.signal)
        self.add_widget(self.external)
        self.add_widget(self.led)
        self.add_widget(self.lbl_clock)
        self.add_widget(self.btn_menu)

        # BACK BUTTON jetzt GANZ RECHTS
        self.add_widget(self.btn_back)

        self._menu_overlay = None
        self.device_menu = None

        # Default channel = GATT (Android parity)
        from dashboard_gui.global_state_manager import GLOBAL_STATE
        GLOBAL_STATE.set_active_channel("gatt")

    # ---------------------------------------------------
    # Back Button Control
    # ---------------------------------------------------
    def update_back_button(self, screen_name):
        if screen_name == "dashboard":
            self.btn_back.opacity = 0
            self.btn_back.disabled = True
            self.btn_back.width = 0           # <<<<< WICHTIG
            self.btn_back.size_hint_x = None
        else:
            self.btn_back.opacity = 1
            self.btn_back.disabled = False
            self.btn_back.width = dp_scaled(40)
            self.btn_back.size_hint_x = None

    def _go_back(self, *_):
        App.get_running_app().root.current = getattr(self, "_back_target", "dashboard")



    def enable_back(self, target="dashboard"):
        self.btn_back.opacity = 1
        self.btn_back.disabled = False
        self.btn_back.width = dp_scaled(40)
        self._back_target = target

    # ---------------------------------------------------
    # Menu overlay
    # ---------------------------------------------------
    def _open_device_menu(self):
        # Falls bereits offen → schließen
        if hasattr(self, "_device_menu") and self._device_menu:
            self.parent.remove_widget(self._device_menu)
            self._device_menu = None
            return
    
        # Liste vom GSM holen
        from dashboard_gui.global_state_manager import GLOBAL_STATE
        device_list = GLOBAL_STATE.get_device_list()
    
        menu = DevicePickerMenu(
            parent_header=self,
            device_list=device_list,
            on_select_device=lambda idx: GLOBAL_STATE.set_active_index(idx)
        )
    
        self._device_menu = menu
        screen = self.parent.parent
        screen.add_widget(menu)


    def _open_menu(self):
        # Falls Menü schon offen ist, nichts tun
        if getattr(self, "_menu_overlay", None):
            return
    
        # WindowPicker erzeugen, HeaderBar als Referenz optional übergeben
        picker = WindowPicker(parent_header=self)
    
        # Overlay speichern, damit wir später schließen können
        self._menu_overlay = picker
    
        # Picker zum Screen hinzufügen
        screen = self.parent.parent
        screen.add_widget(picker)



    # ---------------------------------------------------
    # ONE ENTRY-POINT FOR ALL SCREENS
    # ---------------------------------------------------
    def update_from_global(self, frame):
        """
        Zentrale Update-Funktion für alle Online-Screens.
        Der Screen ruft nur noch: header.update_from_global(out)
        """
        if not frame:
            # safe defaults
            self.set_clock(time.strftime("%H:%M:%S"))
            self.set_device_label(None)
            self.set_rssi(None)
            self.set_external(False)
            return

        # CLOCK
        self.set_clock(time.strftime("%H:%M:%S"))

        # DEVICE LABEL
        self.lbl_dev.text = self._resolve_device_name(frame)


        # RSSI (health.signal bevorzugt)
        self.set_rssi_from_frame(frame)

        # EXTERNAL (health.external bevorzugt, sonst aktiver Channel)
        self.set_external_from_frame(frame)

        # LED:
        # - wird bei dir weiterhin vom GSM gepusht (led_state dict),
        #   aber falls jemand aus Versehen full-frame hier reinreicht,
        #   schadet das nicht:
        if "alive" in frame or "status" in frame:
            self.set_led(frame)


    # ---------------------------------------------------
    # Helpers
    # ---------------------------------------------------
    def _u_bg(self, *_):
        self.bg.pos = self.pos
        self.bg.size = self.size

    def _update_clock(self, *_):
        self.lbl_clock.text = time.strftime("%H:%M")

    def _short_dev(self, dev):
        if not dev: return "---"
        p = dev.split(":")
        return f"{p[0]}:{p[1]} … {p[-1]}" if len(p) == 6 else dev

    def set_device_label(self, frame):
        if isinstance(frame, dict):
            self.lbl_dev.text = self._resolve_device_name(frame)
        elif isinstance(frame, str):
            name = self._name_from_config(frame)
            self.lbl_dev.text = name or self._short_dev(frame)
        else:
            self.lbl_dev.text = "---"
        
    def set_led(self, d):
        self.led.set_state(d.get("alive", False), d.get("status", "offline"))

    def set_external(self, present):
        self.external.set_external(bool(present))

    def set_rssi(self, rssi):
        self.signal.set_rssi(rssi)

    def set_rssi_from_frame(self, frame):
        if not frame:
            self.signal.set_rssi(None)
            return
    
        # 1. RSSI aus dem Health-Bereich (einzige zuverlässige Quelle)
        rssi = None
        try:
            rssi = frame["health"]["signal"]["rssi"]
        except:
            pass
    
        # 2. Falls der Kanal etwas hat (z.B. später pro Kanal RSSI)
        if rssi is None:
            from dashboard_gui.global_state_manager import GLOBAL_STATE
            ch = GLOBAL_STATE.get_active_channel()  # "adv" oder "gatt"
            dec = frame.get(ch)
            if dec:
                # falls Decoder später rssi liefert:
                rssi = dec.get("rssi")
    
        self.signal.set_rssi(rssi)

    def set_clock(self, hhmmss):
        self.lbl_clock.text = hhmmss


    def set_external_from_frame(self, frame):
            """
            Entscheidet kanal-sicher, ob ein EXTERNAL-Sensor vorhanden ist.
            Unterstützt Multi-Channel (adv/gatt).
            """
            if not frame:
                self.set_external(False)
                return
    
            present = False
    
            # 1) HEALTH → höchste Priorität, wenn es existiert
            try:
                present = bool(frame["health"]["external"]["present"])
            except:
                pass
    
            # 2) Falls nicht im Health → aktiver Kanal
            if not present:
                from dashboard_gui.global_state_manager import GLOBAL_STATE
                ch = GLOBAL_STATE.get_active_channel()   # "adv" oder "gatt"
                dec = frame.get(ch)
                if dec and isinstance(dec, dict):
                    present = bool(dec.get("external", {}).get("present", False))
    
            # 3) In UI anwenden
            self.set_external(present)
    def _name_from_config(self, mac):
        try:
            import config
            cfg = config._init()
            dev = cfg.get("devices", {}).get(mac, {})
            return dev.get("name")
        except:
            return None
    def _resolve_device_name(self, frame):
        if not frame:
            return "---"
    
        mac = frame.get("device_id")
        if not mac:
            return "---"
    
        name = self._name_from_config(mac)
        if name:
            return name
    
        return self._short_dev(mac)