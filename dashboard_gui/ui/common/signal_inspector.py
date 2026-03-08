from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.clock import Clock
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
import time 
class SignalGraph(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.points = []
        self.max_points = 60
        # Trigger erstellen
        self._redraw_trigger = Clock.create_trigger(self._do_redraw, -1)

        with self.canvas.after:
            Color(0, 0.8, 1, 0.15)
            self._glow = Line(width=dp_scaled(6), joint='round')
            Color(0, 0.9, 1, 0.7)
            self._line = Line(width=dp_scaled(2.5), joint='round')

        # Hier war der Fehler: Die Methode muss existieren!
        self.bind(pos=self._trigger_redraw, size=self._trigger_redraw)

    def _trigger_redraw(self, *args):
        """Wird aufgerufen, wenn sich Position oder Größe ändern."""
        self._redraw_trigger()

    def add_value(self, val):
        try:
            v = float(val)
            # VIVID SCALE: -90 bis -40 dBm auf 0.0 bis 1.0 spreizen
            normalized = (v + 90) / 50 
            normalized = max(0.05, min(0.95, normalized))
            self.points.append(normalized)
        except: return

        if len(self.points) > self.max_points:
            self.points.pop(0)
        self._redraw_trigger()

    def _do_redraw(self, *args):
        if not self.points or self.width <= 0: return
        w_step = self.width / (self.max_points - 1)
        line_points = []
        for i, p in enumerate(self.points):
            line_points.extend((self.x + (i * w_step), self.y + (p * self.height)))
        
        self._line.points = line_points
        self._glow.points = line_points

    def reset(self):
        self.points = []
        self._line.points = []
        self._glow.points = []

class SignalInspector(FloatLayout):
    def __init__(self, parent_header, **kwargs):
        super().__init__(**kwargs)
        self.parent_header = parent_header
        self.dfe = GLOBAL_STATE.data_flow 
        
        # 1) Hintergrund
        bg = Button(background_color=(0, 0, 0, 0.2), border=(0, 0, 0, 0))
        bg.bind(on_release=lambda *_: self.close())
        self.add_widget(bg)

        # 2) Das Panel (avg_card Style)
        self.panel = FloatLayout(
            size_hint=(None, None),
            size=(dp_scaled(320), dp_scaled(260)), 
            pos_hint={"right": 0.98, "top": 0.98}
        )

        with self.panel.canvas.before:
            Color(0, 0, 0, 0.6) 
            self.panel.bg = RoundedRectangle(pos=self.panel.pos, size=self.panel.size, radius=[dp_scaled(20)])
            Color(0, 0.8, 1, 0.5) 
            self.panel.outline = Line(rounded_rectangle=(self.panel.x, self.panel.y, self.panel.width, self.panel.height, dp_scaled(20)), width=1.2)
        
        self.panel.bind(pos=self._update_panel_canvas, size=self._update_panel_canvas)

        # 3) LAYER 1: Der Graph (Vivid & Background)
        self.graph = SignalGraph(
            size_hint=(0.9, 0.45), 
            pos_hint={"center_x": 0.5, "center_y": 0.35}
        )
        
        # 4) LAYER 2: Der Text
# 4) LAYER 2: Der Text
        # WICHTIG: size_hint=(1, 1) sorgt dafür, dass er das Panel ausfüllt!
        content_text = BoxLayout(
            orientation="vertical", 
            padding=dp_scaled(20),
            size_hint=(1, 1),  # <-- Das hat gefehlt!
            pos_hint={"x": 0, "y": 0} # Damit es genau auf dem Panel liegt
        )

        self.lbl = Label(markup=True, halign="left", valign="top", font_size=sp_scaled(13))
        self.lbl.bind(size=lambda *_: setattr(self.lbl, "text_size", self.lbl.size))
        
        self.raw_lbl = Label(markup=True, halign="left", font_name="RobotoMono-Regular", 
                             font_size=sp_scaled(9), size_hint_y=None, height=dp_scaled(20), 
                             color=(0.5, 0.8, 1, 0.5))
        self.raw_lbl.bind(size=lambda *_: setattr(self.raw_lbl, "text_size", self.raw_lbl.size))

        content_text.add_widget(self.lbl)
        content_text.add_widget(Widget(size_hint_y=None, height=dp_scaled(10)))
        content_text.add_widget(self.raw_lbl)

        self.panel.add_widget(self.graph)
        self.panel.add_widget(content_text)
        self.add_widget(self.panel)

        self.sync_with_global_state()
        self._update_event = Clock.schedule_interval(self.update_ui, 0.2)

    def _update_panel_canvas(self, obj, *args):
        self.panel.bg.pos = obj.pos
        self.panel.bg.size = obj.size
        self.panel.outline.rounded_rectangle = (obj.x, obj.y, obj.width, obj.height, dp_scaled(20))

    def sync_with_global_state(self):
        dev_id = GLOBAL_STATE.get_active_device_id()
        if not dev_id or not self.dfe: return
        self._current_dev_id = dev_id
        self.graph.reset()
        hist = self.dfe.rssi_history.get(dev_id, [])
        for val in hist[-self.graph.max_points:]:
            self.graph.add_value(val)

    def update_ui(self, *_):
        dev_id = GLOBAL_STATE.get_active_device_id()
        if not dev_id: return
        if self._current_dev_id != dev_id: self.sync_with_global_state()

        frame = getattr(self.parent_header, "_last_frame", {})
        channel = frame.get("channel", "adv")
        ch_data = frame.get(channel, {})
        health = frame.get("health", {})

        # RSSI & Graph
        rssi = health.get("signal", {}).get("rssi") or ch_data.get("rssi", "--")
        if rssi != "--":
            self.graph.add_value(rssi)
            rssi_color = "00FF00" if float(rssi) > -65 else ("FFCC00" if float(rssi) > -85 else "FF4444")
        else:
            rssi_color = "888888"

        # Last Seen & Latency
        last_seen = "Never"
        if dev_id in self.dfe.last_seen_timestamps:
            diff = time.time() - self.dfe.last_seen_timestamps[dev_id]
            last_seen = f"{int(diff)}s ago" if diff < 60 else time.strftime("%H:%M:%S", time.localtime(self.dfe.last_seen_timestamps[dev_id]))

        latency = frame.get("latency", 0) / 1000.0
        lat_color = "00FF00" if latency < 2.0 else "FFCC00"

        # Uptime sicher
        uptime_data = health.get("uptime", {})
        uptime_raw = uptime_data.get("value") or 0
        uptime_str = f"{int(uptime_raw//3600):02d}:{int((uptime_raw%3600)//60):02d}:{int(uptime_raw%60):02d}"
        packets = ch_data.get("packet_counter", "0")

        # RAW Data
        raw_val = ch_data.get("raw") or ch_data.get("adv_raw") or "--"
        short_raw = (str(raw_val)[:50] + "...") if len(str(raw_val)) > 50 else str(raw_val)

        # UI Text
        dev_name = GLOBAL_STATE.get_device_label(dev_id)
        self.lbl.text = (
            f"[b][color=00CCFF]{dev_name}[/color][/b] [size=11sp][color=888888]{dev_id}[/color][/size]\n\n"
            f"RSSI     : [color={rssi_color}][b]{rssi} dBm[/b][/color]\n"
            f"Seen     : {last_seen}\n"
            f"Latency  : [color={lat_color}]{latency:.2f}s[/color]\n"
            f"Uptime   : {uptime_str}\n"
            f"Packets  : {packets} ({channel.upper()})"
        )
        self.raw_lbl.text = f"[color=4488FF]RAW:[/color] {short_raw}"

    def close(self):
        if self._update_event:
            self._update_event.cancel()
        if GLOBAL_STATE.ui_handler.active_inspector == self:
            GLOBAL_STATE.ui_handler.active_inspector = None
        if self.parent:
            self.parent.remove_widget(self)