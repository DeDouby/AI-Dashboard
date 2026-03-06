# -*- coding: utf-8 -*-
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, RoundedRectangle, Line
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, RoundedRectangle, Line
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled

class MixedModePanel(BoxLayout):
    def __init__(self, screen, **kw):
        super().__init__(orientation="horizontal", padding=dp_scaled(15), spacing=dp_scaled(20), **kw)
        self.screen = screen
        
        # --- LINKS: Scroll-Liste ---
        self.left_col = BoxLayout(orientation="vertical", size_hint_x=0.35)
        # ... (dein bisheriger Code für left_col)
        self.left_col.add_widget(Label(text="[b]DEVICES[/b]", markup=True, size_hint_y=None, height=dp_scaled(30), color=(1, 1, 1, 0.6)))
        self.scroll = ScrollView(do_scroll_x=False, bar_width=dp_scaled(2))
        self.details_list = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp_scaled(10))
        self.details_list.bind(minimum_height=self.details_list.setter("height"))
        self.scroll.add_widget(self.details_list)
        self.left_col.add_widget(self.scroll)
        self.add_widget(self.left_col)

        # --- RECHTS: Averages Card ---
        self.right_col = BoxLayout(orientation="vertical", size_hint_x=0.65)
        
        # Card-Container (Höhe auf 380 erhöht, damit die dicke Schrift Platz hat)
        self.avg_card = BoxLayout(
            orientation="vertical", 
            padding=dp_scaled(20), 
            spacing=dp_scaled(10), # Spacing etwas verringert, da Schrift größer
            size_hint=(None, None), 
            size=(dp_scaled(400), dp_scaled(380)), 
            pos_hint={"center_x": .5, "center_y": .5}
        )
        
        with self.avg_card.canvas.before:
            Color(0, 0, 0, 0.5)
            self.bg_rect = RoundedRectangle(radius=[dp_scaled(20)])
            Color(1, 1, 1, 0.2)
            self.title_line = Line(width=1)
            
        self.avg_card.bind(pos=self._update_rect, size=self._update_rect)

        # 1. Überschrift
        self.lbl_avg_title = Label(
            text="[b]MIXED AVERAGES[/b]", markup=True, font_size=sp_scaled(22),
            size_hint_y=None, height=dp_scaled(45), color=(1, 1, 1, 0.9),
            halign="center", valign="middle"
        )
        self.lbl_avg_title.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)))
        self.avg_card.add_widget(self.lbl_avg_title)

        # 2. Labels für Werte (Basis-Schriftgröße von 32 auf 42 erhöht)
        # Die Legende und Pfeile werden über das Markup im Handler NOCH größer skaliert
        self.lbl_temp = Label(text="--", markup=True, font_size=sp_scaled(42), color=(1, 0.4, 0.4, 1))
        self.lbl_hum  = Label(text="--", markup=True, font_size=sp_scaled(42), color=(0.4, 0.7, 1, 1))
        self.lbl_vpd  = Label(text="--", markup=True, font_size=sp_scaled(42), color=(0.4, 1, 0.7, 1))
        self.lbl_dew  = Label(text="--", markup=True, font_size=sp_scaled(42), color=(0.8, 0.8, 1, 1))
        
        for l in [self.lbl_temp, self.lbl_hum, self.lbl_vpd, self.lbl_dew]:
            self.avg_card.add_widget(l)
        
        self.right_col.add_widget(Widget()) 
        self.right_col.add_widget(self.avg_card)
        self.right_col.add_widget(Widget()) 
        self.add_widget(self.right_col)

    def _update_rect(self, instance, value):
        # Hintergrund-Rechteck aktualisieren
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size
        
        # Trennlinie unter dem Titel positionieren
        line_y = instance.top - dp_scaled(60)
        self.title_line.points = [instance.x + dp_scaled(40), line_y, instance.right - dp_scaled(40), line_y]

    def set_averages(self, data):
        self.lbl_temp.text = data.get("temp", "--")
        self.lbl_hum.text = data.get("hum", "--")
        self.lbl_vpd.text = data.get("vpd", "--")
        self.lbl_dew.text = data.get("dew", "--")

    def rebuild_device_list(self):
        self.details_list.clear_widgets()
        snapshot = self.screen.handler.get_device_list_snapshot()
        for dev in snapshot:
            self.details_list.add_widget(self._build_card(dev))

    def _build_card(self, dev):
        is_sel = dev["selected"]
        # Farbschema passend zu den Dashboard-Kacheln
        active_color = (0, 0, 0, 0.5)
        inactive_color = (0, 0, 0, 0.2)

        h = dp_scaled(115) if (is_sel and dev["has_external"]) else dp_scaled(75)
        card = BoxLayout(orientation="vertical", size_hint_y=None, height=h, spacing=dp_scaled(4))
        
        # Haupt-Button für das Gerät
        btn = ToggleButton(
            text=f"[b]{dev['label']}[/b]\n[size=13][color=#aaaaaa]{dev['values_str']}[/color][/size]", 
            markup=True, halign="center",
            state="down" if is_sel else "normal",
            background_normal='', background_down='',
            background_color=active_color if is_sel else inactive_color
        )
        btn.bind(on_release=lambda x: self.screen._toggle_dev(dev["device_id"]))
        card.add_widget(btn)

        # Auswahl der Modi (Internal/External)
        if is_sel and dev["has_external"]:
            modes = BoxLayout(spacing=dp_scaled(4), size_hint_y=None, height=dp_scaled(32))
            for m in ["internal", "external"]:
                m_active = m in dev["modes"]
                m_btn = ToggleButton(
                    text=m.upper(), 
                    state="down" if m_active else "normal",
                    font_size=sp_scaled(11), bold=True,
                    background_normal='', background_down='',
                    background_color=(0, 0, 0, 0.5) if m_active else (0, 0, 0, 0.2),
                    color=(1, 1, 1, 1) if m_active else (1, 1, 1, 0.5)
                )
                m_btn.bind(on_release=lambda x, m=m: self.screen._switch_mode(dev["device_id"], m))
                modes.add_widget(m_btn)
            card.add_widget(modes)
        return card