# LightTile: Zeigt den Status der Beleuchtung an, inklusive aktueller Helligkeit, Zielhelligkeit, verbleibender Zeit und Phase des Tages.
import os
import time
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.app import App
from kivy.graphics import Color, RoundedRectangle, Line

from dashboard_gui.ui.scaling_utils import sp_scaled, dp_scaled
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.overlays.light_overlay import LightOverlay
from dashboard_gui.overlays.base_overlay import BaseOverlayEngine
from dashboard_gui.ui.grow_overview_content.segmented_progress_bar import SegmentedProgressBar

ASSET_ROOT = os.path.join("dashboard_gui", "assets")
LIGHT_PIC = os.path.join(ASSET_ROOT, "hardware_pics", "electrogrow.png")


class LightTile(BoxLayout):

    def __init__(self, **kw):
        super().__init__(
            orientation="vertical",
            size_hint=(1, 1),
            **kw
        )
        self.val_box_w = dp_scaled(200)
        self.val_box_h = dp_scaled(140)

        self.padding = dp_scaled(10)
        self.spacing = dp_scaled(6)

        # Titel oben drüber über die ganze Breite
        self.title_label = Label(
            text="ElectroGrow 720W",
            font_size=sp_scaled(20),
            bold=True,
            halign="left",
            valign="middle",
            size_hint=(1, None),
            height=dp_scaled(25),
            color=(1, 1, 1, 1)
        )
        self.title_label.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))

        self._user_active = False
        self._last_user_action = 0
        self._last_sent_rev = 0
        self._ui_lock = False
        self.engine = BaseOverlayEngine()

        # Main Container
        self.content_container = BoxLayout(
            orientation="horizontal",
            size_hint=(1, 1),
            spacing=dp_scaled(2)
        )

        # Value Box (Hintergrund und Rahmen)
        self.value_box = BoxLayout(
            orientation="vertical",
            size_hint=(1, 1), 
            padding=[dp_scaled(12), dp_scaled(10)],
            spacing=dp_scaled(6)
        )
        
# Horizontale Box für die Aufteilung: Links Labels, Rechts Bild
        self.columns_box = BoxLayout(
            orientation="horizontal",
            size_hint=(1, 1),
            spacing=dp_scaled(10)
        )

        # Linke Spalte für die Werte (auf 50% verkleinert, reicht für die Texte völlig)
        self.labels_column = BoxLayout(
            orientation="vertical",
            size_hint=(0.5, 1),
            spacing=dp_scaled(2)
        )

        # Rechte Spalte für das Hardware-Bild (auf 50% verbreitert für maximale Größe)
        self.image_column = BoxLayout(
            orientation="vertical",
            size_hint=(0.5, 1)
        )
        
        self.prog_bar = SegmentedProgressBar()
        self.prog_bar.size_hint = (1, None)
        self.prog_bar.height = dp_scaled(18)                
        
        # Bild füllt nun die vergrößerte 50%-Spalte komplett aus
        self.light_image = Image(
            source=LIGHT_PIC,
            size_hint=(1, 1),
            fit_mode="contain"  # Skaliert das Bild perfekt auf die neue Maximalgröße
        )
        self.image_column.add_widget(self.light_image)
        
        with self.value_box.canvas.before:
            Color(0, 0, 0, 0.62)
            self.value_bg = RoundedRectangle(radius=[dp_scaled(14)])
        
            self.glow_color = Color(1.0, 0.72, 0.15, 0.35)
            self.value_glow = Line(width=5)
        
            self.border_color = Color(1.0, 0.72, 0.15, 0.85)
            self.value_border = Line(width=1.3)

        self.value_box.bind(pos=self._update_value_box_canvas, size=self._update_value_box_canvas)
        self.labels_column.add_widget(self.title_label)
        # Labels initialisieren
        self.lbl_current = Label(text="LIVE: --%", font_size=sp_scaled(20), bold=True,
                                 halign="left", valign="middle", color=(1, 1, 1, 1))
        self.lbl_target = Label(text="TARGET: --%", font_size=sp_scaled(18),
                                halign="left", valign="middle")
        self.lbl_remaining = Label(text="REST: --:--", font_size=sp_scaled(18),
                                   halign="left", valign="middle")
        self.lbl_status = Label(text="STATUS: INIT", font_size=sp_scaled(18),
                                halign="left", valign="middle", markup=True)
        self.lbl_phase = Label(text="PHASE: --", font_size=sp_scaled(18),
                               halign="left", valign="middle", color=(1, 1, 1, 1))

        # Labels in die linke Spalte packen
        for lbl in (self.lbl_current, self.lbl_target, self.lbl_remaining, self.lbl_status, self.lbl_phase):
            lbl.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))
            self.labels_column.add_widget(lbl)

        # Spalten in die übergeordnete horizontale Box einfügen
        self.columns_box.add_widget(self.labels_column)
        self.columns_box.add_widget(self.image_column)

        # Zusammenbau der Value Box von oben nach unten
        self.value_box.add_widget(self.columns_box)    # 2. Spalten (Werte & Bild)
        self.value_box.add_widget(self.prog_bar)       # 3. Progressbar unten

        self.content_container.add_widget(self.value_box)
        self.add_widget(self.content_container)

 
    def _update_box_color(self, brightness):
        if brightness is None or brightness < 0:
            rgb = (0.5, 0.5, 0.5)
        elif brightness <= 0:
            rgb = (0.2, 0.2, 0.2)
        elif brightness < 20:
            rgb = (0.6, 0.5, 0.0)
        elif brightness < 50:
            rgb = (0.8, 0.8, 0.0)
        elif brightness < 80:
            rgb = (1.0, 1.0, 0.0)
        else:
            rgb = (1.0, 1.0, 0.6)
    
        self.glow_color.rgba = (*rgb, 0.35)
        self.border_color.rgba = (*rgb, 0.85)

    def _update_value_box_canvas(self, obj, *args):
        x, y = obj.pos
        w, h = obj.size
        r = dp_scaled(14)
        self.value_bg.pos = (x, y)
        self.value_bg.size = (w, h)
        rect = (x, y, w, h, r)
        self.value_glow.rounded_rectangle = rect
        self.value_border.rounded_rectangle = rect

    # ==================== UPDATE ====================
    def update_values(self, data):
        if not data:
            return

        target = int(data.get('light_target', 0))
        current_hw = int(data.get('light_pct', 0))
        self.prog_bar.value = current_hw
        self.prog_bar.max = 100
        self._update_box_color(current_hw)
        mode = data.get('light_mode', 'man')

        self.lbl_current.text = f"LIVE: {current_hw}%"
        self.lbl_target.text = f"TARGET: {target}%"
        self.lbl_remaining.text = self._calculate_remaining_time(data)

        self._update_phase(data)
        
        server_init = int(data.get('rev_init_light', 0))
        server_rev = int(data.get('rev_light', 0))

        if self.engine.adopt_new_session(server_init, server_rev):
            self._last_sent_rev = server_rev
            return

        status = self.engine.get_status(
            server_init, server_rev, self._user_active, self._last_user_action
        )

        if status == "green":
            if mode == "man":
                self.lbl_status.text = "STATUS: [color=00ff00]MANU[/color]"
            elif mode == "tim":
                self.lbl_status.text = "STATUS: [color=00ff00]TIMER[/color]"
            else:
                self.lbl_status.text = "STATUS: [color=00ff00]OK[/color]"
        elif status in ("retry", "error"):
            self.lbl_status.text = "STATUS: [color=ff4c00]ERR[/color]"
        else:
            self.lbl_status.text = "STATUS: [color=ff8000]PEND[/color]"

    # ==================== PHASE ====================
# ==================== PHASE ====================
    def _update_phase(self, data):
        # Wir nutzen direkt light_state_reason als führenden Wert
        state = str(data.get("light_state_reason", "UNKNOWN")).upper().strip()
        climate_override = bool(data.get("light_climate_override", False))
        
        # Konfiguration für die Phasen
        phase_config = {
            "SUNRISE": {"text": "SUNRISE", "color": (1.0, 0.72, 0.15, 1)},
            "SUNSET":  {"text": "SUNSET",  "color": (1.0, 0.45, 0.1, 1)},
            "NIGHT":   {"text": "NIGHT",   "color": (0.45, 0.65, 1.0, 1)},
            "DAY":     {"text": "DAY",     "color": (1.0, 1.0, 0.6, 1)},
            "UNKNOWN": {"text": "UNKNOWN", "color": (0.5, 0.5, 0.5, 1)}
        }

        # Fallback auf NIGHT, falls etwas Unerwartetes kommt
        config = phase_config.get(state, phase_config["UNKNOWN"])
        
        text = config["text"]
        color = config["color"]
    
        # Climate Override anhängen, falls aktiv
        if climate_override:
            text += " | CLIM"
    
        self.lbl_phase.text = f"PHASE: {text}"
                # Wenn der Grund sehr lang ist, Schriftgröße verringern
        if len(text) > 10:  # Richtwert, ggf. anpassen
            self.lbl_phase.font_size = sp_scaled(16)
        else:
            self.lbl_phase.font_size = sp_scaled(18)
        self.lbl_phase.color = color
    # ==================== TIME ====================
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

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        ui = GLOBAL_STATE.ui_handler
        if getattr(ui, "active_light_overlay", None):
            ui.active_light_overlay.close()

        overlay = LightOverlay(parent_header=self)
        ui.active_light_overlay = overlay
        App.get_running_app().root.current_screen.add_widget(overlay)
        return True