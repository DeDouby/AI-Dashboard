from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.anchorlayout import AnchorLayout
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.clock import Clock
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled

class SignalGraph(Widget):
    """Widget-Graph für den RSSI-Verlauf"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.points = [] 
        self.max_points = 60 
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

# [Gleiche Imports wie vorher...]

class SignalInspector(FloatLayout):
    def __init__(self, parent_header, **kwargs):
        super().__init__(**kwargs)
        self.parent_header = parent_header
        
        # 1) Hintergrund (Klick schließt das Fenster sofort)
        bg = Button(background_color=(0, 0, 0, 0.15), border=(0, 0, 0, 0))
        bg.bind(on_release=lambda *_: self.close())
        self.add_widget(bg)

        # 2) Das Haupt-Panel
        self.panel = AnchorLayout(
            size_hint=(None, None),
            size=(dp_scaled(380), dp_scaled(260)),
            pos_hint={"right": 0.98, "top": 0.98}
        )

        with self.panel.canvas.before:
            Color(0.22, 0.25, 0.30, 0.85) 
            self.panel.bg = RoundedRectangle(pos=self.panel.pos, size=self.panel.size, radius=[12])
        
        self.panel.bind(pos=lambda obj, pos: setattr(self.panel.bg, 'pos', pos),
                        size=lambda obj, size: setattr(self.panel.bg, 'size', size))

        self.graph = SignalGraph(size_hint=(0.9, 0.7))
        self.panel.add_widget(self.graph)

        content = BoxLayout(orientation="vertical", padding=dp_scaled(16), spacing=dp_scaled(5))
        self.lbl = Label(markup=True, halign="left", valign="top", font_size=sp_scaled(15))
        self.lbl.bind(size=lambda *_: setattr(self.lbl, "text_size", self.lbl.size))
        
        content.add_widget(self.lbl)
        self.panel.add_widget(content)
        self.add_widget(self.panel)

        # Timer für UI-Updates
        self._update_event = Clock.schedule_interval(self.update_ui, 0.5)

    def update_ui(self, *_):
        frame = getattr(self.parent_header, "_last_frame", None)
        if not frame: return

        channel = frame.get("channel", "adv")
        ch = frame.get(channel, {}) or {}
        rssi = frame.get("health", {}).get("signal", {}).get("rssi") or ch.get("rssi", "--")
        
        # Den Graphen füttern (er wird beim Öffnen initial mit GSM-Daten befüllt, 
        # hier kriegt er die Live-Updates während er offen ist)
        if rssi != "--":
            self.graph.add_value(rssi)

        packets = ch.get("packet_counter", "--")
        raw = ch.get("raw") or ch.get("adv_raw") or "--"
        rssi_color = "00FF00" if isinstance(rssi, (int, float)) and rssi > -70 else "FFCC00"
        short_raw = (str(raw)[:40] + "...") if len(str(raw)) > 40 else str(raw)

        self.lbl.text = (
            f"[b]Signal Inspector[/b]\n\n"
            f"Device : [b]{frame.get('device_id','?')}[/b]\n"
            f"RSSI   : [b][color={rssi_color}]{rssi} dBm[/color][/b]\n"
            f"Packets: {packets}\n"
            f"Channel: {channel.upper()}\n\n"
            f"[size=18][color=888888]RAW DATA:[/color][/size]\n" 
            f"[size=20][font=RobotoMono-Regular]{short_raw}[/font][/size]"
        )

    def close(self):
        """Zerstört das Widget sauber"""
        if self._update_event:
            self._update_event.cancel()
        if self.parent:
            self.parent.remove_widget(self)
        if self.parent_header:
            self.parent_header._signal_overlay = None