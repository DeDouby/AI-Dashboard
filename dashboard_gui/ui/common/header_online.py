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
import config
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.ui.common.window_picker import WindowPicker
from dashboard_gui.ui.common.device_picker_menu import DevicePickerMenu
from dashboard_gui.ui.common.signal_inspector import SignalInspector
from dashboard_gui.ui.common.broadcast_button import BroadcastButton
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.common.circulation_fan_control import CirculationFanControl
from dashboard_gui.ui.common.exhaust_fan_control import ExhaustFanControl  # <--- NEU
from dashboard_gui.ui.common.light_control import LightControl
from dashboard_gui.ui.common.signal_bars import SignalBars
from dashboard_gui.ui.common.led_circle import LEDCircle
from dashboard_gui.ui.common.icon_label import IconLabel
from dashboard_gui.ui.common.battery_icon import BatteryIcon
from dashboard_gui.ui.common.external_icon import ExternalIcon
from dashboard_gui.ui.common.external2_icon import External2Icon
from dashboard_gui.ui.common.push_message_icon import PushMessageIcon
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
        self.height = dp_scaled(45)   # Etwas höher für besseres Layout
        self.spacing = dp_scaled(10)   # Kleineres Spacing für kompaktere Icons
        # Minimal Padding, Icon-Heavy Design
        self.padding = [dp_scaled(6), dp_scaled(2), dp_scaled(6), dp_scaled(2)]
        self._signal_overlay = None
        self._signal_update_event = None
        with self.canvas.before:
            Color(0.1, 0.1, 0.15, 0.65)
            self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._u_bg, size=self._u_bg)
        self._last_frame = {}
        ########### STATE DICT FÜR ALLE WICHTIGEN DATEN, DIE DER HEADER DARSTELLT ALLES Hier REIN, keine Eigenwege
        self._state = {
            "rssi": None,
            "battery": None,
            "light": None,
            "external": False,
            "external2": False,
            "led_alive": False,
            "led_status": "offline",
            "circulation_fan_rpm": None,
            "exhaust_fan_rpm": None,
        }        
        
        # BACK BUTTON (stabil, bleibt rechts)
        self.btn_back = Button(
            text="\uf060",
            font_name="FA",
            size_hint=(None, 1),
            width=dp_scaled(70),
            background_color=(0.22, 0.25, 0.30, 0.9),
            color=(0.95, 0.95, 0.98, 1),
            font_size=sp_scaled(22),
            opacity=0,
            disabled=True,
        )
        self.btn_back.bind(on_release=lambda *_: self._go_back())

        # LOGO - Fixed Width, nicht proportional
        logo_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "logo.png")
        self.device_icon = Image(
            source=logo_path,
            size_hint=(None, 1),
            width=dp_scaled(40),  # Fixed, nicht fluid
            fit_mode="contain",
            keep_ratio=True,
            pos_hint={'center_y': 0.5}
        )
        

        # DEVICE NAME - Klickbar, Flexible Breite (SPACER)
        self.lbl_dev = Button(
            text="---",
            markup=True,
            font_size=sp_scaled(16),
            size_hint=(1, 1),      # Flexible Mitte
            width=dp_scaled(170),  # Anfangsbreite für Device Name mit Channel
            background_color=(0, 0, 0, 0),
            color=(0.95, 0.95, 0.98, 1),
            halign="left",
            valign="middle",
            padding=(dp_scaled(3), 0),
            shorten=True,
            shorten_from='right',
            text_size=(dp_scaled(170), None),  # Text passt in feste Breite, nicht zweizeilig
        )
        self.lbl_dev.bind(size=lambda instance, _: setattr(instance, 'text_size', (instance.width, instance.height)))
        self.lbl_dev.bind(on_release=lambda *_: self._open_device_menu())
        
        # --- ICONS SECTION (Rechts, alle Fixed Width) ---
        # Signalstärke
        self.signal = SignalBars(size_hint=(None, 1))
        self.signal.width = dp_scaled(40)  # Gleichmäßige Breite
        self.signal.bind(on_touch_down=self._signal_click)
        
        # Externer Sensor
        self.external = ExternalIcon(size_hint=(None, 1))
        self.external.width = dp_scaled(75)  # Gleichmäßige Breite

        # Externer2 Sensor
        self.external2 = External2Icon(size_hint=(None, 1))
        self.external2.width = dp_scaled(75)  # Gleichmäßige Breite

        # Circulation Fan
        self.circulation_fan = CirculationFanControl(
            parent_header=self,
            size_hint=(None, 1),
            width=dp_scaled(40)  # Gleichmäßige Breite
        )
        
        # Exhaust Fan
        self.exhaust_fan = ExhaustFanControl(
            parent_header=self,
            size_hint=(None, 1),
            width=dp_scaled(40)  # Gleichmäßige Breite
        )
        
        # Light Control
        self.light = LightControl(
            parent_header=self,
            size_hint=(None, 1),
            width=dp_scaled(40)  # Gleichmäßige Breite
        )
        # Push Message Icon
        self.push_message = PushMessageIcon(
            size_hint=(None, 1),
            width=dp_scaled(40)
        )
        # Battery
        self.battery = BatteryIcon(size_hint=(None, 1))
        self.battery.width = dp_scaled(70)  # Gleichmäßige Breite
        
        # LED Status
        self.led = LEDCircle(size_hint=(None, 1))
        self.led.width = dp_scaled(40)  # Gleichmäßige Breite
        
        # Broadcast Button
        self.btn_broadcast = BroadcastButton(
            text="\uf09e",
            font_name="FA",
            size_hint=(None, 1),
            width=dp_scaled(40),  # Gleichmäßige Breite
            background_color=(0, 0, 0, 0),
            color=(0.7, 0.7, 0.7, 1),
            font_size=sp_scaled(18)
        )
        
        # Clock
        self.lbl_clock = Label(
            text="--:--",
            font_size=sp_scaled(16),
            size_hint=(None, 1),
            width=dp_scaled(40)  # Gleichmäßige Breite
        )
        Clock.schedule_interval(self._update_clock, 1)

        # MENU BUTTON (Links neben Back)
        self.btn_menu = Button(
            text="\uf0c9",
            font_name="FA",
            size_hint=(None, 1),
            width=dp_scaled(40),  # Gleichmäßige Breite
            background_color=(0.22, 0.25, 0.30, 0.9),
            color=(0.95, 0.95, 0.98, 1),
            font_size=sp_scaled(22)
        )
        self.btn_menu.bind(on_release=lambda *_: self._open_menu())

        # ASSEMBLY - EDGE-LOCK + FLEX-CENTER SYSTEM
        # Left edge anchor: Back and Logo

        self.add_widget(self.device_icon)

        # Center flexible area: branding + device label
        self.center_zone = BoxLayout(size_hint=(1, 1), spacing=dp_scaled(6))

        self.lbl_dev.size_hint = (1, 1)
        self.lbl_dev.width = dp_scaled(170)
        self.center_zone.add_widget(self.lbl_dev)
        self.add_widget(self.center_zone)

        # Right edge icon chain: status, less-important actions, menu anchor
        self.add_widget(self.signal)
        self.add_widget(self.push_message)

        self.add_widget(self.light)
        self.add_widget(self.circulation_fan)
        self.add_widget(self.exhaust_fan)
        self.add_widget(self.btn_broadcast)
        self.add_widget(self.led)
        self.add_widget(self.external)
        self.add_widget(self.external2)
        self.add_widget(self.battery)
        self.add_widget(self.lbl_clock)
        
        self.add_widget(self.btn_menu)
        self.add_widget(self.btn_back)   # << HIERHIN


        self._responsive_items = [
            (self.lbl_clock, 4),
            (self.btn_broadcast, 4),
            (self.battery, 3),
            (self.light, 3),
            (self.exhaust_fan, 3),
            (self.circulation_fan, 3),
            (self.external, 2),
            (self.external2, 2),
            (self.push_message, 2)
        ]
        self._responsive_defaults = {}
        for widget, _ in self._responsive_items:
            self._responsive_defaults[widget] = {
                'width': widget.width,
                'size_hint_x': widget.size_hint_x,
            }

        self.bind(width=self._on_width)
        self._on_width()

        self._menu_overlay = None
        self.device_menu = None




    def _apply_state(self):
        s = self._state
    
        self.signal.set_rssi(s["rssi"])
        self.battery.set_voltage(s["battery"])
        self.light.set_brightness(s["light"])
    
        self.external.set_external(s["external"])
        self.external2.set_external2(s["external2"])
        self.led.set_state(s["led_alive"], s["led_status"])
            # 🔥 FANS FIX
        self.circulation_fan.set_rpm(s["circulation_fan_rpm"])
        self.exhaust_fan.set_rpm(s["exhaust_fan_rpm"])
    
    
    # ---------------------------------------------------
    # Back Button Control
    # ---------------------------------------------------
    def update_back_button(self):
        from dashboard_gui.global_state_manager import GLOBAL_STATE
    
        can_go_back = GLOBAL_STATE.ui_handler.can_go_back()
    
        if can_go_back:
            self.btn_back.opacity = 1
            self.btn_back.disabled = False
            self.btn_back.width = dp_scaled(70)
            self.btn_back.size_hint_x = None
        else:
            self.btn_back.opacity = 0
            self.btn_back.disabled = True
            self.btn_back.width = 0
            self.btn_back.size_hint_x = None

    def _go_back(self, *_):
        App.get_running_app().root.current = getattr(self, "_back_target", "dashboard")

    def _set_responsive_widget(self, widget, visible):
        defaults = self._responsive_defaults.get(widget, {})
        if visible:
            widget.opacity = 1
            widget.disabled = False
            widget.size_hint_x = defaults.get('size_hint_x', None)
            if defaults.get('width') is not None:
                widget.width = defaults['width']
        else:
            widget.opacity = 0
            widget.disabled = True
            widget.size_hint_x = None
            widget.width = 0

    def _on_width(self, *_):
        width = self.width or Window.width
        hide_priority4 = width < dp_scaled(520)
        hide_priority3 = width < dp_scaled(470)
        hide_priority2 = width < dp_scaled(400)

        for widget, priority in self._responsive_items:
            if priority == 4:
                self._set_responsive_widget(widget, not hide_priority4)
            elif priority == 3:
                self._set_responsive_widget(widget, not hide_priority3)
            elif priority == 2:
                self._set_responsive_widget(widget, not hide_priority2)
            else:
                self._set_responsive_widget(widget, True)



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
    
        if not isinstance(frame, dict) or not frame:
            return
    
        web_ch = frame.get("webserver", {})
        
        
        circ_data = web_ch.get("circulation_fan", {})
        exh_data = web_ch.get("exhaust_fan", {})

        self._state["circulation_fan_rpm"] = circ_data.get("circulation_fan_rpm")
        self._state["exhaust_fan_rpm"] = exh_data.get("exhaust_fan_rpm")

        
        health = frame.get("health", {})
    
        # DEVICE LABEL bleibt wie es ist
        mac = frame.get("device_id")
        label = GLOBAL_STATE.get_device_label(mac) if mac else "---"
        ch_name = frame.get("channel", "adv")
        tag = "WEB" if ch_name == "webserver" else ch_name.upper()
        self.lbl_dev.text = f"[font=FA]\uf2c7[/font]  {label} [color=777777]· {tag}[/color]"
    
        # ----------------------------
        # STATE ONLY (KEIN UI LOGIK MEHR)
        # ----------------------------
        self._state["rssi"] = health.get("signal", {}).get("rssi")
    
        self._state["battery"] = (
            health.get("battery", {}).get("voltage")
            or web_ch.get("battery_voltage")
        )
    
        self._state["light"] = web_ch.get("light_pct")
    
        self._state["external"] = bool(
            health.get("external", {}).get("present")
            or web_ch.get("external", {}).get("present", False)
        )
  
        self._state["external2"] = bool(
            health.get("external2", {}).get("present")
            or web_ch.get("external2", {}).get("present", False)
        )
        self._state["led_alive"] = frame.get("alive", False)
        self._state["led_status"] = frame.get("status", "offline")
    
        # EIN EINZIGER APPLY
        self._apply_state()
        self._last_frame = frame.copy()          # <--- WICHTIG
    # === Channel korrekt setzen ===
        active_channel = GLOBAL_STATE.get_active_channel() or "webserver"  # Default sinnvoll
        frame_with_channel = self._last_frame.copy()
        frame_with_channel["channel"] = active_channel
        self._last_frame = frame_with_channel
        self.push_message.update_from_frame(frame)
        self._update_clock()



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

