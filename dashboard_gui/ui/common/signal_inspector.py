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
class SignalGraph(Widget):
    """Widget-Graph für den RSSI-Verlauf"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        import config # Import hier oder oben
        self.points = [] 
        # NEU: Direkt aus der Config laden statt fest auf 60
        self.max_points = config.get_tile_graph_window() 
        self.bind(pos=self.redraw, size=self.redraw)
        self.bind(pos=self.redraw, size=self.redraw)

    def add_value(self, val):
        try:
            v = float(val)
            # Bereich optimiert auf -95 bis -45 dBm
            normalized = (v + 95) / 50 
            normalized = max(0.05, min(0.95, normalized))
            self.points.append(normalized)
        except:
            pass

        if len(self.points) > self.max_points:
            self.points.pop(0)
        self.redraw()

    def redraw(self, *args):
        self.canvas.after.clear()
        if not self.points: return
        
        with self.canvas.after:
            Color(0, 0.8, 1, 0.4) 
            w_step = self.width / (self.max_points - 1)
            line_points = []
            for i, p in enumerate(self.points):
                px = self.x + (i * w_step)
                py = self.y + (p * self.height)
                line_points.extend([px, py])
            
            if len(line_points) >= 4:
                Line(points=line_points, width=3.5, joint='round')

    def reset(self):
        self.points = []
        self.redraw()

class SignalInspector(FloatLayout):
    def __init__(self, parent_header, **kwargs):
        super().__init__(**kwargs)
        self.parent_header = parent_header
        self._last_packet_time = time.time()
        self._latency = 0.0
        
        # 1) Hintergrund
        bg = Button(background_color=(0, 0, 0, 0.15), border=(0, 0, 0, 0))
        bg.bind(on_release=lambda *_: self.close())
        self.add_widget(bg)

        # 2) Das Haupt-Panel (Etwas höher für extra Info)
        self.panel = AnchorLayout(
            size_hint=(None, None),
            size=(dp_scaled(380), dp_scaled(240)), 
            pos_hint={"right": 0.98, "top": 0.98}
        )

        with self.panel.canvas.before:
            Color(0, 0, 0, 0.55) # Dein geiles Schwarz-Transparent
            self.panel.bg = RoundedRectangle(pos=self.panel.pos, size=self.panel.size, radius=[12])
            
            # OPTIONAL: Ein ganz feiner weißer Rand (nur 10% Sichtbarkeit)
            # Das wirkt wie eine Lichtkante und rettet die Lesbarkeit bei dunklen Hintergründen
            Color(1, 1, 1, 0.1) 
            self.panel.outline = Line(rounded_rectangle=(self.panel.x, self.panel.y, self.panel.width, self.panel.height, 12), width=1)
        
        self.panel.bind(pos=lambda obj, pos: setattr(self.panel.bg, 'pos', pos),
                        size=lambda obj, size: setattr(self.panel.bg, 'size', size))

        self.graph = SignalGraph(size_hint=(0.9, 0.6)) # Platz für Text oben/unten
        self.panel.add_widget(self.graph)

        content = BoxLayout(orientation="vertical", padding=dp_scaled(16), spacing=dp_scaled(5))
        self.lbl = Label(markup=True, halign="left", valign="top", font_size=sp_scaled(16))
        self.lbl.bind(size=lambda *_: setattr(self.lbl, "text_size", self.lbl.size))
        
        content.add_widget(self.lbl)
        self.panel.add_widget(content)
        self.add_widget(self.panel)

        self._update_event = Clock.schedule_interval(self.update_ui, 0.5)

    def update_ui(self, *_):
        frame = getattr(self.parent_header, "_last_frame", None)
        if not frame: return

        # --- NEU: GERÄTE-WECHSEL LOGIK (Anti-Mischmasch) ---
        from dashboard_gui.global_state_manager import GLOBAL_STATE
        dev_id = frame.get('device_id', '?')
        
        # Falls das Gerät gewechselt wurde, Graph leeren und Historie laden
        if getattr(self, "_current_dev_id", None) != dev_id:
            self._current_dev_id = dev_id
            self.graph.points = [] # Visueller Reset
            
            # Historie aus GSM Schublade laden (falls vorhanden)
            hist = GLOBAL_STATE.rssi_history.get(dev_id, [])
            for val in hist:
                self.graph.add_value(val)
        
        # Graph-Fenster live synchron halten
        self.graph.max_points = GLOBAL_STATE.trend_window
        # --------------------------------------------------

        # 1) Zeitstempel & Latenz (Heartbeat)
        last_packet = getattr(self.parent_header, "_last_real_packet_time", time.time())
        latency = time.time() - last_packet
        
        # 2) Daten extrahieren
        channel = frame.get("channel", "adv")
        ch = frame.get(channel, {}) or {}
        health = frame.get("health", {})
        
        # RSSI & Graph (Werte werden jetzt im GSM gepuffert, hier nur Anzeige)
        rssi = health.get("signal", {}).get("rssi") or ch.get("rssi", "--")
        if rssi != "--":
            self.graph.add_value(rssi)
            rssi_color = "00FF00" if float(rssi) > -70 else "FFCC00"
        else:
            rssi_color = "888888"

        # 3) Bridge & Uptime Logik
        bridge_status = frame.get("bridge_status", "???")
        bridge_color = "00FF00" if frame.get("bridge_alive") else "FF4444"
        
        # Uptime schön formatieren (Sekunden -> HH:MM:SS)
        uptime_val = health.get("uptime", {}).get("value")
        if uptime_val is not None:
            m, s = divmod(int(uptime_val), 60)
            h, m = divmod(m, 60)
            uptime_str = f"{h:02d}:{m:02d}:{s:02d}"
        else:
            uptime_str = "---"

        # 4) Status-Farben (Heartbeat)
        if latency < 2.5:
            lat_color, status_text = "00FF00", "LIVE"
        elif latency < 10.0:
            lat_color, status_text = "FFCC00", "STALE"
        else:
            lat_color, status_text = "FF4444", "LOST"

        # 5) Raw Data & Name (Config-Abgleich via GSM)
        dev_name = frame.get("name") or GLOBAL_STATE.get_device_label(dev_id)

        packets = ch.get("packet_counter") or "0"
        raw = ch.get("raw") or ch.get("adv_raw") or "--"
        short_raw = (str(raw)[:40] + "...") if len(str(raw)) > 40 else str(raw)

        # 6) Finales UI-Layout
        self.lbl.text = (
            f"[b]{dev_name}[/b]  [color={bridge_color}][size=14sp]Bridge: {bridge_status}[/size][/color]\n"
            f"[color=888888]{dev_id}[/color]\n\n"
            f"RSSI     : [b][color={rssi_color}]{rssi} dBm[/color][/b]\n"
            f"Heartbeat: [b][color={lat_color}]{latency:.1f}s ago[/color][/b] ({status_text})\n"
            f"Uptime   : [b]{uptime_str}[/b]\n"
            f"Packets  : {packets} ({channel.upper()})\n\n"
            f"[color=888888]RAW DATA STREAM:[/color]\n" 
            f"[font=RobotoMono-Regular]{short_raw}[/font]"
        )
    def reset_graph(self):
        if self.graph:
            self.graph.reset()
    def close(self):
        if self._update_event:
            self._update_event.cancel()
        if self.parent:
            self.parent.remove_widget(self)
        if self.parent_header:
            self.parent_header._signal_overlay = None