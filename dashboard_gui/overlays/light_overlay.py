###############################################################################
# !!! REPARIERTES & BEGRADIGTES OVERLAY: HIGH-TECH DESIGN MIT BACKGROUND-GRAPH !!!
# INKLUSIVE ROTEM ZEITINDIKATOR & X-ACHSEN-ZEITLEGENDE
###############################################################################

import os
import json
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.clock import Clock
import time 
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.overlays.unified_slider import UnifiedSlider
from dashboard_gui.overlays.lock_overlay import LockOverlay
from dashboard_gui.overlays.base_overlay import BaseOverlayEngine
from kivy.uix.widget import Widget

class LightOverlay(FloatLayout):
    def __init__(self, parent_header, **kwargs):
        super().__init__(**kwargs)
        self.parent_header = parent_header
        self._user_active = False 
        self._last_user_action = 0 
        self._init_done = False
        self._locked = True
        self._target_mode = "tim"
        self._last_sent_rev = 0
        self._last_send_time = 0
        self._retry_count = 0
        self._max_retries = 5
        self._ui_lock = False
        self._pending_updates = {}
        self.sync_path = os.path.join("data", "settings_sync.json")
        self.engine = BaseOverlayEngine()
        
        # Hintergrund
        bg = Button(background_color=(0, 0, 0, 0.25))
        bg.bind(on_release=lambda *_: self.close())
        self.add_widget(bg)

        # Panel (Abmessungen exakt beibehalten)
        self.panel = BoxLayout(
            orientation="vertical", 
            spacing=dp_scaled(7),
            size_hint=(None, None), 
            size=(dp_scaled(440), dp_scaled(500)), 
            padding=[dp_scaled(25), dp_scaled(15), dp_scaled(25), dp_scaled(25)],
            pos_hint={"right": 0.98, "top": 0.98}
        )

        # Leinwand für Hintergrund-Styling und Tageskurve
        with self.panel.canvas.before:
            Color(0.05, 0.05, 0.05, 0.85) # Tieferes, edleres Anthrazit
            self.bg_rect = RoundedRectangle(radius=[dp_scaled(20)])
            Color(0, 1, 0, 0.25)
            self.outline = Line(width=1.2)
            
            # --- EDLER BACKGROUND GRAPH (Tageskurve) ---
            from kivy.graphics import Mesh
            Color(1, 0.72, 0.05, 0.15) # Schön sichtbares, dezentes Hintergrund-Gold
            self.graph_fill = Mesh(mode='triangle_strip')
            
            Color(1, 0.72, 0.05, 0.08) # Glow
            self.graph_glow = Line(width=dp_scaled(4), joint='round')
            Color(1, 0.72, 0.15, 1.25) # Line
            self.graph_line = Line(width=dp_scaled(1.5), joint='round')

            # --- VERTIKALER ROTER ZEITINDIKATOR ---
            Color(1, 0.2, 0.2, 0.85) 
            self.time_indicator = Line(width=dp_scaled(1.5))

        self.panel.bind(pos=self._u, size=self._u)

        # Header

        title_row = BoxLayout(size_hint_y=None, height=dp_scaled(40), spacing=dp_scaled(5))
        
        self.lbl_title = Label(text="LIGHT CONTROL PRO", bold=True, color=(0, 1, 0, 1),
                               font_size=sp_scaled(18), halign="left", valign="middle")
        self.lbl_title.bind(size=self.lbl_title.setter('text_size'))
        
        self.sync_icon = Button(text="[font=FA]\uf021[/font]", markup=True, font_size=sp_scaled(30),
                                background_color=(0, 0, 0, 0), color=(1, 1, 1, 1), 
                                size_hint_x=None, width=dp_scaled(45))
        
        title_row.add_widget(self.lbl_title)
        title_row.add_widget(self.sync_icon)
        self.panel.add_widget(title_row)

        # === STATUS BEREICH (nur aktueller Wert + Status + Restzeit) ===
        status_box = BoxLayout(size_hint_y=None, height=dp_scaled(50), spacing=dp_scaled(15))
        
        self.lbl_val = Label(text="0%", font_size=sp_scaled(39), bold=True, 
                            size_hint_x=None, width=dp_scaled(115), halign='center')
        
        status_right = BoxLayout(orientation='vertical', size_hint_x=1, spacing=dp_scaled(1))
        self.lbl_status_text = Label(text="STATUS: INIT", font_size=sp_scaled(15.5), bold=True, color=(0, 1, 0, 0.85))
        self.lbl_remaining = Label(text="RESTZEIT: --", font_size=sp_scaled(16.5), color=(1, 1, 0, 1), bold=True)
        
        status_right.add_widget(self.lbl_status_text)
        status_right.add_widget(self.lbl_remaining)
        
        status_box.add_widget(self.lbl_val)
        status_box.add_widget(status_right)
        self.panel.add_widget(status_box)

        # === INTENSITÄT SLIDER MIT BESCHRIFTUNG (SOLL-WERT DARÜBER) ===
        intensity_header = BoxLayout(
            size_hint_y=None,
            height=dp_scaled(24),
            spacing=dp_scaled(4)
        )
        
        self.lbl_intensity = Label(
            text="INTENSITÄT",
            font_size=sp_scaled(17),
            color=(1, 1, 1, 0.9),
            bold=True,
            size_hint_x=None,
            width=dp_scaled(120)
        )
        
        # TARGET %
        self.lbl_slider_target = Label(
            text="0%",
            font_size=sp_scaled(21),
            bold=True,
            color=(0.0, 0.75, 1, 1),
            size_hint_x=None,
            width=dp_scaled(72),
            halign='right',
            valign='middle'
        )
        self.lbl_slider_target.bind(
            size=self.lbl_slider_target.setter('text_size')
        )
        
        # >>> NEU: LIGHT STATE
        self.lbl_light_state = Label(
            text="DAY",
            font_size=sp_scaled(14),
            bold=True,
            color=(0, 1, 0, 0.95),
            size_hint_x=1,
            halign='right',
            valign='middle'
        )
        self.lbl_light_state.bind(
            size=self.lbl_light_state.setter('text_size')
        )
        
        intensity_header.add_widget(self.lbl_intensity)
        intensity_header.add_widget(self.lbl_slider_target)
        intensity_header.add_widget(self.lbl_light_state)
        
        self.panel.add_widget(intensity_header)

        # Haupt-Slider
        self.slider = UnifiedSlider(min=0, max=100, mode='single', size_hint_y=None, height=dp_scaled(38))
        self.slider.bind(value=self._on_slider_change, on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.slider)

        # === Weiter mit Sunrise/Sunset etc. ===

        # === Rest bleibt gleich (Sunrise/Sunset, Start, Dauer...) ===

        # Sunrise/Sunset
        self.lbl_sunrise_sunset = Label(text="RAMPEN: --", markup=True, font_size=sp_scaled(18), color=(1, 0.8, 0.2, 0.8), size_hint_y=None, height=dp_scaled(15))
        self.panel.add_widget(self.lbl_sunrise_sunset)
        self.slider_sunrise_sunset = UnifiedSlider(min=1, max=96, mode='range', fill_entire_track=True)        
        self.slider_sunrise_sunset.bind(min_value=self._on_sunrise_sunset_change, max_value=self._on_sunrise_sunset_change, on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.slider_sunrise_sunset)

        # Startzeit
        self.lbl_start = Label(text="START: --", font_size=sp_scaled(18), size_hint_y=None, height=dp_scaled(15))
        self.panel.add_widget(self.lbl_start)
        self.slider_start = UnifiedSlider(min=0, max=95, mode='single', size_hint_y=None, height=dp_scaled(38))
        self.slider_start.bind(value=self._on_start_change, on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.slider_start)

        # Dauer
        self.lbl_dur = Label(text="DAUER: --", font_size=sp_scaled(18), size_hint_y=None, height=dp_scaled(15))
        self.panel.add_widget(self.lbl_dur)
        self.slider_dur = UnifiedSlider(min=1, max=96, mode='single', size_hint_y=None, height=dp_scaled(38))
        self.slider_dur.bind(value=self._on_dur_change, on_touch_down=self._touch_down, on_touch_up=self._touch_up)
        self.panel.add_widget(self.slider_dur)

        # Etwas weniger Platz vor dem Graphen (da Restzeit jetzt oben ist)
        self.panel.add_widget(Widget(size_hint_y=None, height=dp_scaled(4)))

        # Timeline (X-Achse)
        self.timeline_layout = FloatLayout(size_hint_y=None, height=dp_scaled(15))
        self.lbl_time_00 = Label(text="00:00", font_size=sp_scaled(11), color=(0.82, 0.82, 0.82, 0.92), size_hint=(None, None), size=(dp_scaled(40), dp_scaled(15)))
        self.lbl_time_06 = Label(text="06:00", font_size=sp_scaled(11), color=(0.82, 0.82, 0.82, 0.92), size_hint=(None, None), size=(dp_scaled(40), dp_scaled(15)))
        self.lbl_time_12 = Label(text="12:00", font_size=sp_scaled(11), color=(0.82, 0.82, 0.82, 0.92), size_hint=(None, None), size=(dp_scaled(40), dp_scaled(15)))
        self.lbl_time_18 = Label(text="18:00", font_size=sp_scaled(11), color=(0.82, 0.82, 0.82, 0.92), size_hint=(None, None), size=(dp_scaled(40), dp_scaled(15)))
        
        self.timeline_layout.add_widget(self.lbl_time_00)
        self.timeline_layout.add_widget(self.lbl_time_06)
        self.timeline_layout.add_widget(self.lbl_time_12)
        self.timeline_layout.add_widget(self.lbl_time_18)
        self.panel.add_widget(self.timeline_layout)

        # Buttons
        btn_row = BoxLayout(size_hint_y=None, height=dp_scaled(30), spacing=dp_scaled(8))
        self.btn_man = self._create_styled_btn("MANUELL")
        self.btn_tim = self._create_styled_btn("TIMER")
        self.btn_climate = self._create_styled_btn("CLIMA OVR")
        btn_row.add_widget(self.btn_man)
        btn_row.add_widget(self.btn_tim)
        btn_row.add_widget(self.btn_climate)
        self.panel.add_widget(btn_row)


        self.btn_man.bind(on_release=lambda *_: self._set_mode("man"))
        self.btn_tim.bind(on_release=lambda *_: self._set_mode("tim"))
        self.btn_climate.bind(on_release=lambda *_: self._toggle_climate_override()) # <- Eigene Toggle-Funktion

        self.lock_overlay = LockOverlay(parent=self, panel=self.panel, unlock_callback=self._on_unlock)
        Clock.schedule_once(lambda dt: self.lock_overlay.create(), 0.3)
        Clock.schedule_once(self._init_values, 0.1)
        
        self._update_event = Clock.schedule_interval(self.update_ui, 1.0)
        
        self.add_widget(self.panel)
    
    def _create_styled_btn(self, text):
        return Button(
            text=text,
            markup=True,
            background_normal="",
            background_down="",
            background_color=(0.15, 0.15, 0.15, 1),
            color=(1, 1, 1, 1),  # gleiche Basis wie Exhaust (lesbar default)
            font_size=sp_scaled(18)
        )
    def _init_values(self, *_):
        mac = GLOBAL_STATE.get_active_device_id()
        data = GLOBAL_STATE.overlay_engine.get_buffer_data(mac)
        if not data: Clock.schedule_once(self._init_values, 0.3); return
        self._my_handshake_id = self.engine.create_handshake()
        GLOBAL_STATE.overlay_engine.send_light_handshake(mac, self._my_handshake_id)
        self._ui_lock = True
        self._apply_server_snapshot(data)
        self._ui_lock = False
        self._init_done = True
        self._update_graph()

    def _apply_server_snapshot(self, data):
        if not data:
            return
    
        mode = data.get('light_mode', 'man')
    
        phase = str(
            data.get('light_phase', 'DAY')
        ).upper()
    
        climate_override = bool(
            data.get('light_climate_override', False)
        )
    
        state_reason = str(
            data.get('light_state_reason', '')
        ).upper().strip()
    
        target = int(data.get('light_target', 0))
        current_hw = int(data.get('light_pct', 0))
    
        h = int(data.get('l_start_h', 8))
        m = int(data.get('l_start_m', 0))
    
        dur = int(data.get('l_dur', 720))
        srise = int(data.get('l_sunrise', 60))
        sset = int(data.get('l_sunset', 60))
    
        # =====================================================
        # CURRENT VALUE COLOR
        # =====================================================
    
        if mode == "tim" and current_hw != target and current_hw > 0:
            self.lbl_val.color = (1, 0.72, 0.05, 1)
        else:
            self.lbl_val.color = (1, 1, 1, 1)
    
        self.lbl_val.text = f"{current_hw}%"
        self.lbl_slider_target.text = f"{target}%"
    
        # =====================================================
        # BASE LIGHT PHASE
        # =====================================================
    
        if phase == "MORNING":
    
            base_text = "SUNRISE"
            base_color = (1.0, 0.72, 0.15, 1)
    
        elif phase == "EVENING":
    
            base_text = "SUNSET"
            base_color = (1.0, 0.45, 0.1, 1)
    
        elif phase == "NIGHT":
    
            base_text = "NIGHT"
            base_color = (0.45, 0.65, 1.0, 1)
    
        else:
    
            base_text = "DAY"
            base_color = (0.0, 1.0, 0.35, 1)
    
        # =====================================================
        # STATE EXTENSIONS
        # =====================================================
    
        extensions = []
    
        # -----------------------------------------------------
        # CLIMATE OVERRIDE FLAG
        # -----------------------------------------------------
    
        if climate_override:
    
            extensions.append(
                "[color=00ff66]CLIM-OVR[/color]"
            )
    
        # -----------------------------------------------------
        # STATE REASON
        # -----------------------------------------------------
    
        ignored_reasons = {
            "",
            "MANUAL",
            "NORMAL",
            "DAY",
            "TIMER"
        }
    
        if state_reason not in ignored_reasons:
    
            extensions.append(
                f"[color=ffcc33]{state_reason}[/color]"
            )
    
        # =====================================================
        # FINAL LIGHT STATE LABEL
        # =====================================================
    
        final_text = base_text
    
        if extensions:
    
            final_text += " | " + " | ".join(extensions)
    
        self.lbl_light_state.markup = True
        self.lbl_light_state.text = final_text
        self.lbl_light_state.color = base_color
    
        # =====================================================
        # STATUS TEXT
        # =====================================================
    
        if mode == "off":
    
            self.lbl_status_text.text = "STATUS: AUS"
            self.lbl_status_text.color = (1, 0.2, 0.2, 0.8)
    
        elif mode == "man":
    
            self.lbl_status_text.text = "STATUS: MANUELL"
            self.lbl_status_text.color = (0, 0.8, 1, 1)
    
        else:
    
            self.lbl_status_text.text = "STATUS: TIMER"
            self.lbl_status_text.color = (0, 1, 0, 1)
    
        # =====================================================
        # SLIDERS
        # =====================================================
    
        self.slider.value = target
    
        self.slider_start.value = (
            (h * 60 + m) // 15
        )
    
        dur_steps = dur // 15
    
        self.slider_dur.value = dur_steps
    
        self.slider_sunrise_sunset.range_max = dur_steps
    
        self.slider_sunrise_sunset.min_value = (
            srise // 15
        )
    
        self.slider_sunrise_sunset.max_value = (
            dur_steps - (sset // 15)
        )
    
        # =====================================================
        # LABELS
        # =====================================================
    
        self.lbl_start.text = (
            f"START: {h:02d}:{m:02d}"
        )
    
        self.lbl_dur.text = (
            f"DAUER: {dur//60}h {dur%60:02d}m"
        )
    
        # =====================================================
        # FINALIZE
        # =====================================================
    
        self._update_ramp_label(srise, sset)
    
        self._apply_button_styles(
            mode,
            target
        )
    
        self._update_graph()
    def _update_graph(self, *args):
        if not self._init_done: return
        try:
            target = int(self.slider.value)
            start_min = int(self.slider_start.value) * 15
            dur_min = int(self.slider_dur.value) * 15
            srise_min = int(self.slider_sunrise_sunset.min_value) * 15
            sset_min = int(self.slider_sunrise_sunset.range_max - self.slider_sunrise_sunset.max_value) * 15
        except Exception:
            return

        # Koordinaten-Mapping auf Basis der festen Panel-Größe
        x_base = self.panel.x + dp_scaled(25)
        y_base = self.panel.y + dp_scaled(75) 
        w_graph = self.panel.width - dp_scaled(50)
        h_graph = dp_scaled(30) 

        points = []
        end_min = start_min + dur_min

        for step in range(97):
            t = (step * 15) % 1440
            if step == 96: t = 1440
            
            is_active = False
            t_rel = 0

            if end_min <= 1440:
                if start_min <= t <= end_min:
                    is_active = True
                    t_rel = t - start_min
            else:
                if t >= start_min:
                    is_active = True
                    t_rel = t - start_min
                elif t <= (end_min % 1440):
                    is_active = True
                    t_rel = t + 1440 - start_min

            pct = 0
            if is_active and dur_min > 0:
                if t_rel < srise_min and srise_min > 0:
                    pct = target * (t_rel / srise_min)
                elif t_rel > (dur_min - sset_min) and sset_min > 0:
                    pct = target * ((dur_min - t_rel) / sset_min)
                else:
                    pct = target

            x_p = x_base + (step / 96.0) * w_graph
            y_p = y_base + (pct / 100.0) * h_graph
            points.extend([x_p, y_p])

        self.graph_line.points = points
        self.graph_glow.points = points

        vertices = []
        for i in range(0, len(points), 2):
            x_p = points[i]
            y_p = points[i+1]
            vertices.extend([x_p, y_base, 0, 0])
            vertices.extend([x_p, y_p, 0, 0])

        self.graph_fill.indices = list(range(len(vertices) // 4))
        self.graph_fill.vertices = vertices

        # --- POSITION DER ROTEN TIME-LINE ---
        now = time.localtime()
        current_total_minutes = now.tm_hour * 60 + now.tm_min
        day_progress = current_total_minutes / 1440.0
        indicator_x = x_base + (day_progress * w_graph)
        
        self.time_indicator.points = [
            indicator_x, y_base, 
            indicator_x, y_base + h_graph + dp_scaled(5)
        ]

        # --- NEU: DYNAMISCHE POSITIONIERUNG DER ZEIT-LABEL (LEGENDE) ---
        # Wir platzieren die Label relativ zur X-Achse des Graphen um Verschiebungen zu verhindern
        self.lbl_time_00.pos = (x_base - self.lbl_time_00.width / 2, y_base - dp_scaled(16))
        self.lbl_time_06.pos = (x_base + (0.25 * w_graph) - self.lbl_time_06.width / 2, y_base - dp_scaled(16))
        self.lbl_time_12.pos = (x_base + (0.50 * w_graph) - self.lbl_time_12.width / 2, y_base - dp_scaled(16))
        self.lbl_time_18.pos = (x_base + (0.75 * w_graph) - self.lbl_time_18.width / 2, y_base - dp_scaled(16))

    def _calculate_remaining_time(self, data):
        mode = data.get('light_mode', 'man')
        if mode != "tim": 
            return "MODUS: MANUELL/AUS"
        
        h, m = int(data.get('l_start_h', 8)), int(data.get('l_start_m', 0))
        dur = int(data.get('l_dur', 720))

        now = time.localtime()
        current_min = now.tm_hour * 60 + now.tm_min
        start_min = h * 60 + m
        end_min = (start_min + dur)

        is_active = False
        if end_min <= 1440:
            if start_min <= current_min < end_min: is_active = True
        else:
            if current_min >= start_min or current_min < (end_min % 1440): is_active = True

        if is_active:
            rem_min = (end_min - current_min) if current_min >= start_min else ((end_min % 1440) - current_min)
            return f"RESTZEIT: {rem_min // 60}h {rem_min % 60:02d}m"
        else:
            wait_min = (start_min - current_min + 1440) % 1440
            return f"STARTET IN: {wait_min // 60}h {wait_min % 60:02d}m"



    def _on_slider_change(self, *args):
        if self._init_done and not self._ui_lock and not self._locked:
            value = int(self.slider.value)
            self.lbl_slider_target.text = f"{value}%"      # nur noch hier
            self.sync_icon.color = (1, 0.5, 0, 1)
            self._update_graph()

    def _on_dur_change(self, instance, value):
        if self._init_done and not self._ui_lock:
            steps = max(1, min(96, int(value)))
            self.slider_dur.value = steps
            self.lbl_dur.text = f"DAUER: {(steps*15)//60}h {(steps*15)%60:02d}m"
            self.slider_sunrise_sunset.range_max = steps
            self._update_graph()

    def _on_start_change(self, instance, value):
        if self._init_done and not self._ui_lock:
            value = max(0, min(95, int(value)))
            m = value * 15
            self.lbl_start.text = f"START: {m//60:02d}:{m%60:02d}"
            self._update_graph()

    def _update_ramp_label(self, sr, ss):
        self.lbl_sunrise_sunset.text = f"[font=FA]\uf185[/font] SUNRISE: {sr}m | [font=FA]\uf186[/font] SUNSET: {ss}m"

    def _on_sunrise_sunset_change(self, *args):
        if self._init_done and not self._ui_lock:
            sr, ss = int(self.slider_sunrise_sunset.min_value) * 15, int(self.slider_sunrise_sunset.range_max - self.slider_sunrise_sunset.max_value) * 15
            self._update_ramp_label(sr, ss)
            self._update_graph()

    def _touch_down(self, slider, touch):
        if not self._locked and slider.collide_point(*touch.pos): self._user_active = True

    def _touch_up(self, slider, touch):
        if self._user_active:
            self._user_active = False; self._last_user_action = time.time(); self._send_command()

    def _set_mode(self, mode):
        if not self._locked: self._target_mode = mode; self._send_command(mode=mode)

    def _on_unlock(self):
        self._locked = False
        for s in [self.slider, self.slider_start, self.slider_dur, self.slider_sunrise_sunset]: s.disabled = False

    def _force_sync(self, *_): self._send_command()

    def update_ui(self, *_):
        mac = GLOBAL_STATE.get_active_device_id()
        server_data = GLOBAL_STATE.overlay_engine.get_buffer_data(mac)
        if not server_data: return

        self.lbl_remaining.text = self._calculate_remaining_time(server_data)
        server_init = int(server_data.get('rev_init_light', 0))
        server_rev = int(server_data.get('rev_light', 0))
        
        if self.engine.adopt_new_session(server_init, server_rev):
            self._last_sent_rev = server_rev
            return
        
        is_alive = self.engine.is_alive(server_init)
        pending = self.engine.is_pending(server_rev)
        
        if pending and self.engine.should_retry():
            if self.engine.retry_allowed():
                self.engine.register_retry()
                self._send_command(is_retry=True)
                return
        
        status = self.engine.get_status(server_init, server_rev, self._user_active, self._last_user_action)
        
        if status == "green":
            self.sync_icon.text, self.sync_icon.color = "[font=FA]\uf058[/font]", (0, 1, 0, 1)
        elif status == "retry":
            self.sync_icon.text, self.sync_icon.color = "[font=FA]\uf021[/font]", (1, 0.5, 0, 1)
        elif status == "error":
            self.sync_icon.text, self.sync_icon.color = "[font=FA]\uf071[/font]", (1, 0.3, 0, 1)
        else:
            self.sync_icon.text, self.sync_icon.color = "[font=FA]\uf021[/font]", (1, 0.5, 0, 1)
        
        self._update_graph()

        if status != "green": return
        if not self._user_active:
            self._ui_lock = True; self._apply_server_snapshot(server_data); self._ui_lock = False

    def _toggle_climate_override(self):
        if not self._locked:
            mac = GLOBAL_STATE.get_active_device_id()
            server_data = GLOBAL_STATE.overlay_engine.get_buffer_data(mac)
            # Aktuellen Zustand invertieren
            current_override = server_data.get('light_climate_override', False)
            new_override = not current_override
            
            # Befehl mit neuem Override-Zustand absenden
            self._send_command(climate_override=new_override)

    def _send_command(self, is_retry=False, **kwargs):
        mac = GLOBAL_STATE.get_active_device_id()
        if not mac or not self._init_done: return
        start_min = max(0, min(95, int(self.slider_start.value))) * 15
        
        # Hol den Klima-Zustand: Entweder aus den kwargs (frischer Klick) oder aus dem UI-Buffer-Zustand
        server_data = GLOBAL_STATE.overlay_engine.get_buffer_data(mac)
        climate_state = kwargs.get("climate_override", server_data.get('light_climate_override', False))

        rev = GLOBAL_STATE.send_overlay_command(
            "light", 
            pct=int(self.slider.value), 
            mode=kwargs.get("mode", self._target_mode),
            h=start_min // 60, 
            m=start_min % 60, 
            dur=int(self.slider_dur.value) * 15,
            sunrise=int(self.slider_sunrise_sunset.min_value) * 15, 
            sunset=int(self.slider_sunrise_sunset.range_max - self.slider_sunrise_sunset.max_value) * 15,
            climate_override=climate_state # <- Wird an die Engine übergeben
        )
        if rev:
            self.engine.mark_sent(rev)
            self._last_sent_rev = rev
            self._last_send_time = time.time()
            if not is_retry: self.engine.reset_retry()

    def _apply_button_styles(self, mode, target=0):
    
        base = (0.15, 0.15, 0.15, 1)
    
        # MANUAL
        self.btn_man.background_color = (0, 1, 0, 0.85) if mode == "man" else base
    
        # TIMER
        self.btn_tim.background_color = (0, 0.7, 1, 0.85) if mode == "tim" else base
    
        # CLIMATE (ESP LIVE STATUS)
        mac = GLOBAL_STATE.get_active_device_id()
        server_data = GLOBAL_STATE.overlay_engine.get_buffer_data(mac)
        climate_active = server_data.get('light_climate_override', False)
    
        self.btn_climate.background_color = (1, 0.5, 0, 0.85) if climate_active else base
    
        # 🔥 TEXT KONTRAST FIX (EXHAUST 1:1 übernommen)
        def fix(btn, active):
            btn.color = (0, 0, 0, 1) if active else (1, 1, 1, 1)
    
        fix(self.btn_man, mode == "man")
        fix(self.btn_tim, mode == "tim")
        fix(self.btn_climate, climate_active)
        
    def _u(self, *_):
        self.bg_rect.pos, self.bg_rect.size = self.panel.pos, self.panel.size
        self.outline.rounded_rectangle = (self.panel.x, self.panel.y, self.panel.width, self.panel.height, dp_scaled(20))
        self._update_graph()

    def close(self):
        if self._update_event: self._update_event.cancel()
        if self.parent: self.parent.remove_widget(self)
        GLOBAL_STATE.ui_handler.active_light_overlay = None