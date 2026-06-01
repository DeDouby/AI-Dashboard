from kivy.uix.boxlayout import BoxLayout

from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.ui.common.icon_label import IconLabel
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import Color, Line, RoundedRectangle

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
    
            self.accent = (0.1, 0.8, 0.2, 0.6)
    # --------------------------------------------------
    # RECURSIVE SCANNER
    # --------------------------------------------------

    def _find_critical_states(self, data):
    
        found = []
    
        if isinstance(data, dict):
    
            for key, value in data.items():
    
                if (
                    isinstance(key, str)
                    and key.endswith("_reason")
                    and isinstance(value, str)
                ):
    
                    if (
                        value.startswith("CRIT_")
                        or value.startswith("failsafe")
                    ):
                        found.append(value)
    
                found.extend(
                    self._find_critical_states(value)
                )
    
        elif isinstance(data, list):
    
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