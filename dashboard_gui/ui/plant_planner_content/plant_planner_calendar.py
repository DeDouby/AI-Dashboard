# =============================================================================
# DATE PICKER
# =============================================================================
import calendar  # <-- Wichtig: Oben zu den Imports hinzufügen!
from kivy.uix.button import Button
from kivy.graphics import Color, Line
from datetime import date
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.scrollview import ScrollView
from kivy.properties import StringProperty
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.ui.plant_planner_content.glass_button import GlassButton
from kivy.metrics import dp
from kivy.app import App
import os
class DatePickerPopup(Popup):
    selected_date = StringProperty("")

    def __init__(self, callback=None, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self.title = "SELECT DATE"
        self.size_hint = (0.92, 0.85)
        self.auto_dismiss = False

        today = date.today()
        self.current_year = today.year
        self.current_month = today.month

        # 1. Root-Layout (hier gehören padding/spacing hin)
        self.root_layout = BoxLayout(
            orientation="vertical",
            padding=dp_scaled(15),
            spacing=dp_scaled(10)
        )

        # 2. Header
        self.header_box = BoxLayout(size_hint_y=None, height=dp_scaled(50), spacing=dp_scaled(10))
        self.prev_btn = GlassButton(text="<", size_hint_x=0.2)
        self.prev_btn.bind(on_release=self._prev_month)
        self.month_label = Label(text="", font_size=sp_scaled(18), bold=True, size_hint_x=0.6)
        self.next_btn = GlassButton(text=">", size_hint_x=0.2)
        self.next_btn.bind(on_release=self._next_month)
        
        self.header_box.add_widget(self.prev_btn)
        self.header_box.add_widget(self.month_label)
        self.header_box.add_widget(self.next_btn)
        self.root_layout.add_widget(self.header_box)

        # 3. ScrollView mit dem Grid
        self.scroll = ScrollView()
        self.days_grid = GridLayout(cols=7, spacing=dp_scaled(4), size_hint_y=None)
        # WICHTIG: Grid an ScrollView binden
        self.days_grid.bind(minimum_height=self.days_grid.setter('height'))
        self.scroll.add_widget(self.days_grid)
        self.root_layout.add_widget(self.scroll)

        # 4. Footer
        btn_box = BoxLayout(size_hint_y=None, height=dp_scaled(52), spacing=dp_scaled(10))
        cancel_btn = GlassButton(text="CANCEL")
        save_btn = GlassButton(text="SAVE")
        cancel_btn.bind(on_release=lambda *_: self.dismiss())
        save_btn.bind(on_release=self._save)
        btn_box.add_widget(cancel_btn)
        btn_box.add_widget(save_btn)
        self.root_layout.add_widget(btn_box)

        self.content = self.root_layout
        self._update_calendar_view()
    def _update_calendar_view(self):
        """Generiert das Tage-Grid basierend auf current_month & current_year völlig neu."""
        self.days_grid.clear_widgets()

        # Header-Text updaten (z.B. "MAY 2026")
        month_name = calendar.month_name[self.current_month].upper()
        self.month_label.text = f"{month_name} {self.current_year}"

        # Wochentage als kleine Header-Kürzel hinzufügen (Optional, aber extrem hilfreich)
        for day_name in ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]:
            self.days_grid.add_widget(Label(
                text=day_name, 
                size_hint_y=None, 
                height=dp_scaled(30),
                font_size=sp_scaled(18),
                color=(0.5, 0.5, 0.5, 1)
            ))

        # Berechnen, mit welchem Wochentag der Monat startet und wie viele Tage er hat
        # monthrange liefert (weekday_of_first_day, number_of_days). 0 = Montag
        first_weekday, num_days = calendar.monthrange(self.current_year, self.current_month)
        
        # WICHTIG: Setze die Höhe des Grids basierend auf der Anzahl der Zeilen
        # (Header-Reihe + Tage-Reihen)
        total_cells = first_weekday + num_days
        rows = (total_cells // 7) + (1 if total_cells % 7 != 0 else 0) + 1 # +1 für Wochentag-Labels
        self.days_grid.height = rows * dp_scaled(48 + 4) # ca. Höhe pro Zeile + spacing

        # Leere Plätze für den Versatz vor dem 1. des Monats einfügen
        for _ in range(first_weekday):
            self.days_grid.add_widget(Label(size_hint_y=None, height=dp_scaled(48)))

        # Buttons für die echten Tage generieren
        for d in range(1, num_days + 1):
            btn = ToggleButton(
                text=str(d),
                group="date_picker",
                size_hint_y=None,
                height=dp_scaled(48),
                background_color=(0.15, 0.15, 0.2, 1)
            )
            btn.bind(on_release=self._select_day)
            self.days_grid.add_widget(btn)

    def _prev_month(self, *_):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self._update_calendar_view()

    def _next_month(self, *_):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self._update_calendar_view()

    def _select_day(self, btn):
        # Nutzt jetzt die dynamisch ausgewählten Werte statt date.today()
        self.selected_date = (
            f"{self.current_year}-{self.current_month:02d}-{int(btn.text):02d}"
        )

    def _save(self, *_):
        if self.callback and self.selected_date:
            self.callback(self.selected_date)
        self.dismiss()


