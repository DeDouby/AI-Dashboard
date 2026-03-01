from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.anchorlayout import AnchorLayout
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.clock import Clock
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
import time
import time
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.clock import Clock
from kivy.metrics import dp as dp_scaled
from kivy.metrics import sp as sp_scaled

# Import des GSM
from dashboard_gui.global_state_manager import GLOBAL_STATE

class SignalGraph(Widget):
    """Performance-optimierter RSSI Graph"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.points = []
        self.max_points = 60

        # Redraw Trigger (nur 1x pro Frame)
        self._redraw_trigger = Clock.create_trigger(self._do_redraw, -1)

        # Canvas einmalig aufbauen
        with self.canvas.after:
            Color(0, 0.8, 1, 0.4)
            self._line = Line(width=3.5, joint='round')

        # Nur Triggern, nicht direkt zeichnen
        self.bind(pos=self._trigger_redraw,
                  size=self._trigger_redraw)

    # ----------------------------
    # Trigger Handling
    # ----------------------------

    def _trigger_redraw(self, *args):
        self._redraw_trigger()

    # ----------------------------
    # Daten hinzufügen
    # ----------------------------

    def add_value(self, val):
        try:
            v = float(val)
            normalized = (v + 95) / 50
            normalized = max(0.05, min(0.95, normalized))
            self.points.append(normalized)
        except (ValueError, TypeError):
            return

        if len(self.points) > self.max_points:
            self.points.pop(0)

        self._redraw_trigger()

    # ----------------------------
    # ECHTES Redraw
    # ----------------------------

    def _do_redraw(self, *args):
        if not self.points:
            self._line.points = []
            return

        w_step = self.width / (self.max_points - 1)

        line_points = []
        for i, p in enumerate(self.points):
            px = self.x + (i * w_step)
            py = self.y + (p * self.height)
            line_points.extend((px, py))

        self._line.points = line_points

    def reset(self):
        self.points = []
        self._line.points = []
class SignalInspector(FloatLayout):
    def __init__(self, parent_header, **kwargs):
        super().__init__(**kwargs)
        self.parent_header = parent_header
        self._current_dev_id = None
        Clock.schedule_once(self._init_graph_data, 0)
        # 1) Hintergrund (Abbrechen bei Klick außerhalb)
        bg = Button(background_color=(0, 0, 0, 0.15), border=(0, 0, 0, 0))
        bg.bind(on_release=lambda *_: self.close())
        self.add_widget(bg)

        # 2) Das Haupt-Panel
        self.panel = AnchorLayout(
            size_hint=(None, None),
            size=(dp_scaled(300), dp_scaled(220)), 
            pos_hint={"right": 0.98, "top": 0.98}
        )

        with self.panel.canvas.before:
            Color(0, 0, 0, 0.7) # Hintergrund etwas dunkler für bessere Lesbarkeit
            self.panel.bg = RoundedRectangle(pos=self.panel.pos, size=self.panel.size, radius=[12])
            
            # Feine Lichtkante
            Color(1, 1, 1, 0.1) 
            self.panel.outline = Line(rounded_rectangle=(self.panel.x, self.panel.y, self.panel.width, self.panel.height, 12), width=1)
        
        self.panel.bind(pos=lambda obj, pos: setattr(self.panel.bg, 'pos', pos),
                        size=lambda obj, size: setattr(self.panel.bg, 'size', size))
        self.panel.bind(pos=lambda obj, pos: setattr(self.panel.outline, 'rounded_rectangle', (pos[0], pos[1], obj.width, obj.height, 12)),
                        size=lambda obj, size: setattr(self.panel.outline, 'rounded_rectangle', (obj.x, obj.y, size[0], size[1], 12)))

        # Graph-Widget hinzufügen (Fix auf 100 Points)
        self.graph = SignalGraph(size_hint=(0.9, 0.6))
        self.panel.add_widget(self.graph)

        # Text-Content
        content = BoxLayout(orientation="vertical", padding=dp_scaled(16), spacing=dp_scaled(5))
        self.lbl = Label(markup=True, halign="left", valign="top", font_size=sp_scaled(15))
        self.lbl.bind(size=lambda *_: setattr(self.lbl, "text_size", self.lbl.size))
        
        content.add_widget(self.lbl)
        self.panel.add_widget(content)
        self.add_widget(self.panel)

        # Update-Zyklus
        self._update_event = Clock.schedule_interval(self.update_ui, 0.5)

    def update_ui(self, *_):
        # Frame direkt vom Header beziehen (der vom GSM gefüttert wird)
        frame = getattr(self.parent_header, "_last_frame", None)
        if not frame: 
            return

        dev_id = frame.get('device_id', '?')
        
        # --- GERÄTE-WECHSEL / INITIALISIERUNG ---
        if self._current_dev_id != dev_id:
            self._current_dev_id = dev_id
            self.graph.reset()
            
            # Historie direkt aus GSM (rssi_history) abgreifen
            # Wir nehmen nur die letzten 100 Werte, falls GSM mehr hat
            hist = GLOBAL_STATE.rssi_history.get(dev_id, [])
            if hist:
                for val in hist[-100:]:
                    self.graph.add_value(val)

        # 1) Zeitstempel & Latenz
        last_packet = getattr(self.parent_header, "_last_real_packet_time", time.time())
        latency = time.time() - last_packet
        
        # 2) Daten extrahieren
        channel = frame.get("channel", "adv")
        ch = frame.get(channel, {}) or {}
        health = frame.get("health", {})
        
        # RSSI-Wert
        rssi = health.get("signal", {}).get("rssi") or ch.get("rssi", "--")
        
        if rssi != "--":
            # Live-Update des Graphen
            self.graph.add_value(rssi)
            rssi_val = float(rssi)
            if rssi_val > -65: rssi_color = "00FF00" # Exzellent
            elif rssi_val > -85: rssi_color = "FFCC00" # Okay
            else: rssi_color = "FF4444" # Kritisch
        else:
            rssi_color = "888888"

        # 3) Bridge & Uptime
        bridge_status = frame.get("bridge_status", "UNKNOWN")
        bridge_alive = frame.get("bridge_alive", False)
        bridge_color = "00FF00" if bridge_alive else "FF4444"
        
        uptime_val = health.get("uptime", {}).get("value")
        if uptime_val is not None:
            m, s = divmod(int(uptime_val), 60)
            h, m = divmod(m, 60)
            uptime_str = f"{h:02d}:{m:02d}:{s:02d}"
        else:
            uptime_str = "---"

        # 4) Latenz-Farben
        if latency < 3.0:
            lat_color, status_text = "00FF00", "LIVE"
        elif latency < 15.0:
            lat_color, status_text = "FFCC00", "STALE"
        else:
            lat_color, status_text = "FF4444", "LOST"

        # 5) Namen und Identifier über GSM auflösen
        dev_name = GLOBAL_STATE.get_device_label(dev_id)
        packets = ch.get("packet_counter") or "0"
        raw = ch.get("raw") or ch.get("adv_raw") or ch.get("gat_raw") or "--"
        
        # Raw Data kürzen für Anzeige
        raw_str = str(raw)
        short_raw = (raw_str[:42] + "...") if len(raw_str) > 42 else raw_str

        # 6) UI Text zusammenbauen
        self.lbl.text = (
            f"[b]{dev_name}[/b]  [color={bridge_color}][size=13sp]Bridge: {bridge_status}[/size][/color]\n"
            f"[color=888888][size=12sp]{dev_id}[/size][/color]\n\n"
            f"RSSI     : [b][color={rssi_color}]{rssi} dBm[/color][/b]\n"
            f"Heartbeat: [b][color={lat_color}]{latency:.1f}s ago[/color][/b] ({status_text})\n"
            f"Uptime   : [b]{uptime_str}[/b]\n"
            f"Packets  : {packets} ({channel.upper()})\n\n"
            f"[color=888888]RAW DATA STREAM:[/color]\n" 
            f"[font=RobotoMono-Regular][size=12sp]{short_raw}[/size][/font]"
        )

    def _init_graph_data(self, *_):
        frame = getattr(self.parent_header, "_last_frame", None)
        if not frame:
            return
    
        dev_id = frame.get("device_id")
        if not dev_id:
            return
    
        hist = GLOBAL_STATE.rssi_history.get(dev_id, [])
        for val in hist[-self.graph.max_points:]:
            self.graph.add_value(val)
    def close(self):
        if self._update_event:
            self._update_event.cancel()
        if self.parent:
            self.parent.remove_widget(self)
        if self.parent_header:
            self.parent_header._signal_overlay = None

    def reset_graph(self):
        if self.graph:
            self.graph.reset()