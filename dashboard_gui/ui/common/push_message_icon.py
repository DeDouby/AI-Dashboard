from kivy.uix.boxlayout import BoxLayout

from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.ui.common.icon_label import IconLabel
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import Color, Line, RoundedRectangle
from dashboard_gui.global_state_manager import GLOBAL_STATE
class PushMessageIcon(BoxLayout):

    def __init__(self, **kw):
        super().__init__(**kw)

        self.orientation = "horizontal"
        self.size_hint = (None, 1)
        self.width = dp_scaled(40)

        self.icon = IconLabel(
            text="\uf0f3",  # Bell
            font_size=sp_scaled(22)
        )

        self.icon.color = (0.6, 0.6, 0.6, 1)
        self.critical_messages = []
        self._overlay = None
        # DEFAULTS
        self.title_text = (
            "[font=FA]\uf00c[/font] "
            "[b]System Healthy[/b]"
        )
        
        self.accent = (0, 0.8, 1, 0.4)        
        self.add_widget(self.icon)

    # --------------------------------------------------
    # PUBLIC
    # --------------------------------------------------
    def update_from_frame(self, frame):
    
        self.critical_messages = self._find_critical_states(frame)
    
        if self.critical_messages:
    
            self.icon.color = (1, 0.2, 0.2, 1)
    
            self.title_text = (
                "[font=FA]\uf057[/font] "
                "[b]Critical Messages[/b]"
            )
    
            self.accent = (1, 0.25, 0.25, 0.6)
    
        else:
    
            self.icon.color = (0.6, 0.6, 0.6, 1)
    
            self.title_text = (
                "[font=FA]\uf00c[/font] "
                "[b]System Healthy[/b]"
            )
    
# --------------------------------------------------
    # RECURSIVE SCANNER (Case-Insensitive & Dual Field)
    # --------------------------------------------------

    def _find_critical_states(self, data):
        """
        Durchsucht die Daten rekursiv nach kritischen Zuständen in den Feldern
        _reason_1 und _reason_2, unabhängig von Groß- und Kleinschreibung.
        """
        found = []
    
        if isinstance(data, dict):
    
            for key, value in data.items():
                
                # Prüfen, ob der Key ein String ist und auf _reason_1 ODER _reason_2 endet
                if isinstance(key, str) and isinstance(value, str):
                    key_lower = key.lower()
                    
                    if key_lower.endswith("_reason_1") or key_lower.endswith("_reason_2"):
                        
                        # Wert für den Check komplett in Kleinbuchstaben umwandeln
                        val_lower = value.lower()
    
                        # Erkennt jetzt "CRIT...", "crit...", "FAILSAFE...", "failsafe..."
                        if (
                            val_lower.startswith("crit")
                            or val_lower.startswith("failsafe")
                        ):
                            # Wir fügen den originalen Wert (value) hinzu,
                            # damit das UI die echte Schreibweise behält.
                            found.append(value)
    
                # Rekursiv tiefer in Dictionaries graben
                found.extend(
                    self._find_critical_states(value)
                )
    
        elif isinstance(data, list):
    
            # Rekursiv durch Listen gehen
            for item in data:
                found.extend(
                    self._find_critical_states(item)
                )
    
        return found
    def on_touch_down(self, touch):
    
        if not self.collide_point(*touch.pos):
            return False
    
        if self._overlay:
    
            self.close_overlay()
    
        else:
    
            self.open_overlay()
    
        return True
    
    def open_overlay(self):
    
        overlay = FloatLayout()
    
        bg = Button(
            background_color=(0, 0, 0, 0.2),
            border=(0, 0, 0, 0)
        )
    
        bg.bind(on_release=lambda *_: self.close_overlay())
    
        overlay.add_widget(bg)
    
        panel = FloatLayout(
            size_hint=(None, None),
            size=(dp_scaled(320), dp_scaled(260)),
            pos_hint={"right": 0.98, "top": 0.94}
        )



        # --- NEU: Jump-Button Pattern vom SignalInspector ---
        jump_btn = Button(
            text="[font=FA]\uf013[/font]", # Zahnrad oder anderes Icon
            markup=True,
            size_hint=(None, None),
            size=(dp_scaled(40), dp_scaled(40)),
            pos_hint={"right": 0.98, "top": 0.98},
            background_color=(0, 0, 0, 0),
            color=(0, 0.8, 1, 0.8)
        )
        
        # Glass-Look für den Button
        with jump_btn.canvas.before:
            Color(0, 0.8, 1, 0.2)
            jump_bg = RoundedRectangle(radius=[dp_scaled(10)])
            Color(0, 0.8, 1, 0.5)
            jump_line = Line(width=1.1)
            
        def update_btn_canvas(obj, *args):
            jump_bg.pos = obj.pos
            jump_bg.size = obj.size
            jump_line.rounded_rectangle = (obj.x, obj.y, obj.width, obj.height, dp_scaled(10))
            
        jump_btn.bind(pos=update_btn_canvas, size=update_btn_canvas)
        
        # Navigation-Logik
        def jump_to_overview(*_):
            GLOBAL_STATE.ui_handler.goto("grow_overview")
            self.close_overlay() # Overlay sauber schließen

        jump_btn.bind(on_release=jump_to_overview)
        panel.add_widget(jump_btn)
        # --- ENDE NEU ---

        # ... (restlicher Code für Label/Content)‚   
        with panel.canvas.before:
    
            Color(0, 0, 0, 0.6)
    
            panel.bg = RoundedRectangle(
                pos=panel.pos,
                size=panel.size,
                radius=[dp_scaled(20)]
            )
    
            Color(*self.accent)
    
            panel.outline = Line(
                rounded_rectangle=(
                    panel.x,
                    panel.y,
                    panel.width,
                    panel.height,
                    dp_scaled(20)
                ),
                width=1.2
            )
    
        def update_canvas(obj, *_):
    
            panel.bg.pos = obj.pos
            panel.bg.size = obj.size
    
            panel.outline.rounded_rectangle = (
                obj.x,
                obj.y,
                obj.width,
                obj.height,
                dp_scaled(20)
            )
    
        panel.bind(pos=update_canvas, size=update_canvas)



        title = Label(
            text=self.title_text,
            markup=True,
            font_size=sp_scaled(18),
            size_hint=(1, None),
            height=dp_scaled(40),
            pos_hint={
                "center_x": 0.5,
                "top": 0.95
            },
            halign="center",
            valign="middle"
        )
        
        title.bind(
            size=lambda inst, *_: setattr(inst, "text_size", inst.size)
        )
    
        panel.add_widget(title)
    
        if self.critical_messages:

            text = "\n".join(
                f"[color=ff6666]• {msg}[/color]"
                for msg in self.critical_messages
            )

        else:

            text = (
                "[color=55ff55]"
                "No active critical messages"
                "[/color]"
            )
    
            text = "No active critical messages"
    
        content = Label(
            text=text,
            markup=True,
            halign="left",
            valign="top",
            font_size=sp_scaled(16),
            text_size=(dp_scaled(260), None),
            pos_hint={"center_x": 0.5, "center_y": 0.45}
        )
    
        panel.add_widget(content)
    
        overlay.add_widget(panel)
    
        self._overlay = overlay
    
        App.get_running_app().root.current_screen.add_widget(
            overlay
        )
    
    def close_overlay(self):
    
        if self._overlay and self._overlay.parent:
    
            self._overlay.parent.remove_widget(
                self._overlay
            )
    
        self._overlay = None