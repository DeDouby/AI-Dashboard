# -------------------------------------------------------
# header_online.py — FINAL FIXED MINIMAL PATCH
# -------------------------------------------------------

import time
import os

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.graphics import Color, Rectangle, Ellipse, RoundedRectangle
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.metrics import dp, sp
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
import config
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.ui.common.window_picker import WindowPicker
from dashboard_gui.ui.common.device_picker_menu import DevicePickerMenu
from dashboard_gui.ui.common.signal_inspector import SignalInspector
from dashboard_gui.ui.common.broadcast_button import BroadcastButton
from dashboard_gui.global_state_manager import GLOBAL_STATE

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
        self.size_hint = (None, 1)
        self.width = dp_scaled(45) 
        self.padding = [0, 0] # <--- WICHTIG: Kein Padding mehr hier!

        self.img = Image(
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(1, 1), # <--- Auf 1 setzen für maximale Größe
            pos_hint={'center_y': 0.5}
        )
        self.add_widget(self.img)

        # absoluter Pfad zu /dashboard_gui/assets/icons/signal
        self._icon_dir = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "assets", "icons", "signal"
        )

        # Default: kein Signal
        self.set_rssi(None)

    def _panel_bg(self, panel):
        panel.canvas.before.clear()
        with panel.canvas.before:
            Color(0.05,0.05,0.08,0.95)
            Rectangle(pos=panel.pos,size=panel.size)
    def _close_signal_overlay(self):
        if self._signal_overlay and self._signal_overlay.parent:
            self._signal_overlay.parent.remove_widget(self._signal_overlay)
        self._signal_overlay = None

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
# External Sensor – OPTIMIZED FOR 60DP HEADER
# -------------------------------------------------------
class ExternalIcon(BoxLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.orientation = "horizontal" # Von vertikal auf horizontal gewechselt
        self.spacing = dp_scaled(4)
        self.size_hint = (None, 1)
        self.width = dp_scaled(65)      # Etwas breiter für Icon + Text nebeneinander

        # Icon etwas kleiner, damit es nicht "schreit"
        self.icon = IconLabel(font_size=sp_scaled(18))
        
        # Text-Label zentrieren
        self.text_label = Label(
            font_size=sp_scaled(12), 
            color=(0.8, 0.8, 0.8, 1),
            halign="left",
            valign="middle"
        )
        self.text_label.bind(size=self.text_label.setter('text_size'))

        self.add_widget(self.icon)
        self.add_widget(self.text_label)

        self.set_external(False)

    def set_external(self, present):
        if present:
            self.icon.text = "\uf2c7" # Thermometer Icon
            self.icon.color = (0.3, 1, 0.3, 1) # Giftgrün
            self.text_label.text = "EXT"
            self.text_label.color = (0.3, 1, 0.3, 1)
        else:
            self.icon.text = "\uf059" # Fragezeichen
            self.icon.color = (0.4, 0.4, 0.4, 1)
            self.text_label.text = "OFF"
            self.text_label.color = (0.4, 0.4, 0.4, 1)


#######BATTERY
class BatteryIcon(BoxLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.orientation = "horizontal"
        self.spacing = dp_scaled(4)
        self.size_hint = (None, 1)
        self.width = dp_scaled(75) # Platz für Icon + "4.1V"

        self.icon = IconLabel(font_size=sp_scaled(18))
        self.text_label = Label(
            text="--V",
            font_size=sp_scaled(12),
            color=(0.8, 0.8, 0.8, 1),
            halign="left",
            valign="middle"
        )
        self.text_label.bind(size=self.text_label.setter('text_size'))

        self.add_widget(self.icon)
        self.add_widget(self.text_label)

    def set_voltage(self, voltage):
        if voltage is None or voltage < 0.1:
            self.icon.text = "\uf244" # Batterie leer Icon
            self.icon.color = (0.4, 0.4, 0.4, 1)
            self.text_label.text = "OFF"
            return

        self.text_label.text = f"{float(voltage):.2f}V"
        
        # Farblogik & Icons
        if voltage >= 3.9:
            self.icon.text = "\uf240" # Full
            self.icon.color = (0.3, 1, 0.3, 1) # Grün
        elif voltage >= 3.6:
            self.icon.text = "\uf242" # Half
            self.icon.color = (1, 0.8, 0.2, 1) # Gelb
        else:
            self.icon.text = "\uf243" # Low
            self.icon.color = (1, 0.2, 0.2, 1) # Rot
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



#--------------------------------------------------------
# HEADER BAR
# -------------------------------------------------------
class HeaderBar(BoxLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        from dashboard_gui.global_state_manager import GLOBAL_STATE
        self.gsm = GLOBAL_STATE
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp_scaled(40)   # <--- DEIN FIX (überall gleich)
        self.spacing = dp_scaled(12)
        # Weniger Padding oben/unten, damit das Logo größer wirken kann
        self.padding = [dp_scaled(10), dp_scaled(2), dp_scaled(10), dp_scaled(2)]
        self._signal_overlay = None
        self._signal_update_event = None  # für auto-refresh
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

        # LOGO FIX
        logo_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "logo.png")
        self.device_icon = Image(
            source=logo_path,
            size_hint=(None, 1),      # 1 bedeutet: Fülle die volle verfügbare Höhe
            width=dp_scaled(80),      # Gib ihm Platz in der Breite
            allow_stretch=True,
            keep_ratio=True,
            # Das sorgt dafür, dass es wirklich mittig klebt
            pos_hint={'center_y': 0.5} 
        )
        self.device_icon.height = self.height
        
        # Logo an Header-Höhe binden
        def _update_logo_size(*_):
            self.device_icon.height = self.height
            # Breite proportional, automatisch wegen keep_ratio
        self.bind(height=_update_logo_size)
        
        # TEXT & ICONS
        self.lbl_title = Label(
            text="Dashboard",
            font_size=sp_scaled(22),
            halign="left",
            size_hint=(0.28, 1)
        )
        
        self.lbl_dev = Button(
            text="---",
  
            markup=True,
            font_size=sp_scaled(20),
            size_hint=(0.22, 1),
            background_color=(0, 0, 0, 0),
            color=(0.95, 0.95, 0.98, 1),
            halign="left",
            valign="middle",
            padding=(dp_scaled(6), 0),
            text_size=(None, None),
        )
        self.lbl_dev.bind(on_release=lambda *_: self._open_device_menu())
        
        self.signal = SignalBars(size_hint=(0.09, 1))
        self.signal.bind(on_touch_down=self._signal_click)
        self.external = ExternalIcon(size_hint=(0.08, 1))
        self.battery = BatteryIcon(size_hint=(0.09, 1))
        self.led = LEDCircle(size_hint=(0.07, 1))
        # Broadcast Button (Inline wiederhergestellt – KEIN Refactoring jetzt!)
        from dashboard_gui.global_state_manager import GLOBAL_STATE
        
        self.btn_broadcast = BroadcastButton(
            text="\uf09e",
            font_name="FA",
            size_hint=(0.08, 1),
            background_color=(0, 0, 0, 0),
            color=(0.7, 0.7, 0.7, 1),
            font_size=sp_scaled(22)
        )
        
        # NEU: BROADCAST TOGGLE BUTTON
        from dashboard_gui.global_state_manager import GLOBAL_STATE

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
        # Widgets in der richtigen Reihenfolge adden:
        self.add_widget(self.device_icon)
        self.add_widget(self.lbl_title)
        self.add_widget(self.lbl_dev)
        self.add_widget(self.signal)
        self.add_widget(self.btn_broadcast) # <--- NEU HIER
        self.add_widget(self.external)
        self.add_widget(self.battery) # <--- HIER EINREIHEN
        self.add_widget(self.led)
        self.add_widget(self.lbl_clock)
        self.add_widget(self.btn_menu)
        self.add_widget(self.btn_back)

        self._menu_overlay = None
        self.device_menu = None





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

    def _signal_click(self, widget, touch):
        if not widget.collide_point(*touch.pos):
            return False
    
        # Wir fragen den globalen UI-Manager
        ui = self.gsm.ui_handler
        
        if ui.active_inspector:
            ui.close_signal_inspector()
        else:
            ui.open_signal_inspector(parent_header=self)
    
        return True




    def _close_signal_overlay(self):
        """Falls extern geschlossen werden muss"""
        if self._signal_overlay:
            self._signal_overlay.close()


    # ---------------------------------------------------
    # Menu overlay
    # ---------------------------------------------------
    def _open_device_menu(self):
        if getattr(self, "_device_menu", None):
            self._device_menu.close()
            return
    
        from dashboard_gui.global_state_manager import GLOBAL_STATE
        from dashboard_gui.ui.common.device_picker_menu import DevicePickerMenu
    
        device_list = GLOBAL_STATE.get_device_list()
    
        menu = DevicePickerMenu(
            parent_header=self,
            device_list=device_list,
            on_select_device=lambda idx: GLOBAL_STATE.set_active_index(idx)
        )
    
        self._device_menu = menu
    
        # nur EIN add_widget, NICHT zweimal!
        App.get_running_app().root.current_screen.add_widget(menu)

    # Window Picker Menü ----------------
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
        """Wird im Takt der DataFlowEngine gerufen - Einzige Quelle für das Label!"""
        if not isinstance(frame, dict):
            return

        # --- DEVICE & CHANNEL LABEL ---
        self._last_frame = frame  # <--- DIESE ZEILE MUSS REIN!
        mac = frame.get("device_id")
        if mac:
            label = GLOBAL_STATE.get_device_label(mac)
            
            # Hier holen wir den Kanal aus dem Frame, den ACE & DataFlowEngine gesetzt haben
            ch = frame.get("channel", "adv")
            tag = str(ch).upper()
            
            icon = "[font=FA]\uf2c7[/font]"
            # Wir setzen das Label NUR HIER
            self.lbl_dev.text = f"{icon}  {label} [color=777777]· {tag}[/color]"
        else:
            self.lbl_dev.text = "---"
# ... (dein bestehender Code) ...

        # --- BATTERY UPDATE ---
        health = frame.get("health", {})
        # Wir nehmen die Spannung aus der health-Sektion, die du im Decoder befüllst
        v_bat = health.get("battery", {}).get("voltage")
        self.battery.set_voltage(v_bat)
        # --- Restliche Updates ---
        self.set_rssi_from_frame(frame)
        self.set_external_from_frame(frame)
        self._update_clock()

    def set_rssi_from_frame(self, frame):
        """Aktualisiert die Signal-Balken (PNG-Version)"""
        # Daten aus dem neuen Paketformat holen
        health = frame.get("health", {})
        rssi = health.get("signal", {}).get("rssi")
        
        # Du hast in __init__: self.signal = SignalBars(...)
        # Wir rufen also die Methode der Klasse SignalBars auf
        if rssi is not None:
            self.signal.set_rssi(rssi)
        else:
            self.signal.set_rssi(None)
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

 
    def set_led(self, d):
        self.led.set_state(d.get("alive", False), d.get("status", "offline"))



    def set_external(self, present):
        self.external.set_external(bool(present))

    def set_rssi(self, rssi):
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
                ch = frame.get("channel", "adv")  # Standard auf "adv"
                dec = frame.get(ch, {})
                present = bool(dec.get("external", {}).get("present", False))
    
            # 3) In UI anwenden
            self.set_external(present)
