# dashboard_gui/ui/plant_planner_content/plant_planner_screen.py
# TARGET-REVISION v2.0 READY
# ESP AUTHORITATIVE VERSION
# © 2026 Dominik Rosenthal

import copy
import os
import time
from datetime import datetime, date

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Line
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton

from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled

ASSET_ROOT = os.path.join("dashboard_gui", "assets")


# =============================================================================
# GLASS BUTTON
# =============================================================================

class GlassButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.background_normal = ""
        self.background_color = (0.1, 0.1, 0.15, 0.55)
        self.color = (1, 1, 1, 1)
        self.font_size = sp_scaled(18)

        self.bind(pos=self._update_canvas, size=self._update_canvas)

    def _update_canvas(self, *_):
        self.canvas.after.clear()

        with self.canvas.after:
            Color(0, 1, 0.4, 0.45)
            Line(
                rectangle=(self.x, self.y, self.width, self.height),
                width=dp(1.1)
            )


# =============================================================================
# DATE PICKER
# =============================================================================
import calendar  # <-- Wichtig: Oben zu den Imports hinzufügen!

class DatePickerPopup(Popup):
    selected_date = StringProperty("")

    def __init__(self, callback=None, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self.title = "SELECT DATE"
        self.size_hint = (0.92, 0.85)
        self.auto_dismiss = False

        # Start mit dem aktuellen Monat und Jahr
        today = date.today()
        self.current_year = today.year
        self.current_month = today.month

        # Root-Layout
        self.root_layout = BoxLayout(
            orientation="vertical",
            padding=dp_scaled(15),
            spacing=dp_scaled(10)
        )

        # =========================================================
        # MONATS- / JAHRESAUSWAHL (HEADER)
        # =========================================================
        self.header_box = BoxLayout(
            size_hint_y=None,
            height=dp_scaled(50),
            spacing=dp_scaled(10)
        )

        self.prev_btn = GlassButton(text="<", size_hint_x=0.2)
        self.prev_btn.bind(on_release=self._prev_month)

        self.month_label = Label(
            text="", 
            font_size=sp_scaled(18), 
            bold=True,
            size_hint_x=0.6
        )

        self.next_btn = GlassButton(text=">", size_hint_x=0.2)
        self.next_btn.bind(on_release=self._next_month)

        self.header_box.add_widget(self.prev_btn)
        self.header_box.add_widget(self.month_label)
        self.header_box.add_widget(self.next_btn)
        
        self.root_layout.add_widget(self.header_box)

        # =========================================================
        # TAGE GRID & SCROLLVIEW
        # =========================================================
        self.scroll = ScrollView()
        self.days_grid = GridLayout(cols=7, spacing=dp_scaled(4))
        self.scroll.add_widget(self.days_grid)
        
        self.root_layout.add_widget(self.scroll)

        # =========================================================
        # UNTERE BUTTONS (CANCEL / SAVE)
        # =========================================================
        btn_box = BoxLayout(
            size_hint_y=None,
            height=dp_scaled(52),
            spacing=dp_scaled(10)
        )

        cancel_btn = GlassButton(text="CANCEL")
        save_btn = GlassButton(text="SAVE")

        cancel_btn.bind(on_release=lambda *_: self.dismiss())
        save_btn.bind(on_release=self._save)

        btn_box.add_widget(cancel_btn)
        btn_box.add_widget(save_btn)
        self.root_layout.add_widget(btn_box)

        self.content = self.root_layout

        # Initialen Kalender zeichnen
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

# =============================================================================
# SCREEN
# =============================================================================

class PlantPlannerScreen(Screen):

    name = "plant_planner"

    PHASES = [
        "germination",
        "seedling",
        "vegetative",
        "flowering",
        "drying",
        "curing"
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        GLOBAL_STATE.ui_handler.attach_screen(
            "plant_planner",
            self
        )

        self.plants = []

        self.search_text = ""

        self._my_init_rev = 0
        self._last_sent_rev = 0
        self._last_send_time = 0
        self._retry_count = 0
        self._max_retries = 5
        self._last_day = date.today()
        
        Clock.schedule_interval(
            self._check_day_rollover,
            30
        )        
        # =========================================================
        # ROOT
        # =========================================================

        self.root = BoxLayout(orientation="vertical")

        with self.root.canvas.before:
            Color(1, 1, 1, 1)
        
            self.bg_img = Rectangle(
                source=os.path.join(
                    ASSET_ROOT,
                    "background_about.png"
                ),
                pos=self.root.pos,
                size=self.root.size
            )
        
        self.root.bind(
            pos=lambda *_: setattr(self.bg_img, "pos", self.root.pos),
            size=lambda *_: setattr(self.bg_img, "size", self.root.size)
        )

        # =========================================================
        # HEADER
        # =========================================================

        self.header = HeaderBar()
        self.header.set_title("PLANT PLANNER")
        self.header.update_back_button("plant_planner")

        self.root.add_widget(self.header)

        # =========================================================
        # SEARCH
        # =========================================================

        topbar = BoxLayout(
            size_hint_y=None,
            height=dp_scaled(60),
            padding=[dp_scaled(15), dp_scaled(10)],
            spacing=dp_scaled(10)
        )

        self.search_input = TextInput(
            hint_text="SEARCH PLANTS...",
            multiline=False,
            background_color=(0.1, 0.1, 0.12, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0.2, 1, 0.4, 1),
            font_size=sp_scaled(18)
        )

        self.search_input.bind(text=self._on_search)

        add_btn = GlassButton(
            text="+ NEW",
            size_hint_x=None,
            width=dp_scaled(110)
        )

        add_btn.bind(on_release=lambda *_: self.open_edit_popup())

        topbar.add_widget(self.search_input)
        topbar.add_widget(add_btn)

        self.root.add_widget(topbar)

        # =========================================================
        # SCROLL
        # =========================================================

        self.scroll = ScrollView(
            do_scroll_x=False,
            bar_width=dp(4)
        )

        self.body = GridLayout(
            cols=1,
            spacing=dp_scaled(12),
            padding=dp_scaled(15),
            size_hint_y=None
        )

        self.body.bind(
            minimum_height=self.body.setter("height")
        )

        self.scroll.add_widget(self.body)

        self.root.add_widget(self.scroll)

        self.add_widget(self.root)

        # =========================================================

        Clock.schedule_interval(
            self._check_sync_status,
            1.0
        )

    # =============================================================================
    # ENTER
    # =============================================================================

    def on_enter(self):
        Clock.schedule_once(lambda *_: self._force_resync(), 0.3)
        Clock.schedule_once(lambda *_: self._force_reload_plants(), 0.7)  # neu

    # =============================================================================
    # BG
    # =============================================================================



    # =============================================================================
    # HANDSHAKE
    # =============================================================================

    def _force_resync(self):

        mac = GLOBAL_STATE.get_active_device_id()

        if not mac:
            return

        self._my_init_rev = int(time.time())

        GLOBAL_STATE.overlay_engine.send_plant_planner_handshake(
            mac,
            self._my_init_rev
        )

    # =============================================================================
    # PUSH
    # =============================================================================

    def _push_plants_to_esp(self):

        new_rev = GLOBAL_STATE.send_overlay_command(
            "plant_planner",
            plants=self.plants
        )

        if new_rev:
            self._last_sent_rev = new_rev
            self._last_send_time = time.time()
            self._retry_count = 0

            print(
                f"[PlantPlanner] PUSH -> REV {new_rev}"
            )

    def _force_reload_plants(self):
        mac = GLOBAL_STATE.get_active_device_id()
        if mac:
            data = GLOBAL_STATE.overlay_engine.get_buffer_data(mac)
            self.update_from_global(data)
    # =============================================================================
    # SEARCH
    # =============================================================================

    def _on_search(self, instance, value):
        self.search_text = value.lower().strip()
        self.build_ui()

    def _filtered_plants(self):

        if not self.search_text:
            return self.plants

        result = []

        for p in self.plants:

            blob = (
                str(p.get("name", "")) +
                str(p.get("strain", "")) +
                str(p.get("breeder", ""))
            ).lower()

            if self.search_text in blob:
                result.append(p)

        return result

    # =============================================================================
    # UI
    # =============================================================================
# =============================================================================
    # UI (OPTIMIERT: ASYNCHRONES / PROGRESSIVES LADEN)
    # =============================================================================

    def build_ui(self):
        # 1. Altes Zeug löschen
        self.body.clear_widgets()

        # 2. Eventuell noch laufende Ladevorgänge abbrechen
        Clock.unschedule(self._load_cards_progressive)

        filtered = self._filtered_plants()

        if not filtered:
            empty = Label(
                text="NO PLANTS FOUND",
                size_hint_y=None,
                height=dp_scaled(120),
                font_size=sp_scaled(20),
                color=(0.7, 0.7, 0.7, 1)
            )
            self.body.add_widget(empty)
            return

        # 3. Starte das stufenweise Laden ab Index 0
        self._load_cards_progressive(filtered, 0)

    def _load_cards_progressive(self, plant_list, index, *args):
        """ Schiebt Karte für Karte in den nächsten Frame, damit die UI nicht einfriert. """
        # Sicherheitscheck: Sind wir schon am Ende der Liste?
        if index >= len(plant_list):
            return

        # Sicherheitscheck: Hat der User den Screen während des Ladens verlassen?
        if self.manager and self.manager.current != self.name:
            return

        # Baue GENAU EINE Karte
        plant = plant_list[index]
        card = self._build_plant_card(plant)
        self.body.add_widget(card)

        # Plane die nächste Karte für den exakt nächsten Frame (0 Sekunden Verzögerung) ein
        Clock.schedule_once(lambda dt: self._load_cards_progressive(plant_list, index + 1), 0)


    # =============================================================================
    # CARD
    # =============================================================================

    def _build_plant_card(self, plant):

        card = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=dp_scaled(14),
            spacing=dp_scaled(10)
        )

        card.height = dp_scaled(280)

        with card.canvas.before:
            Color(0.08, 0.08, 0.12, 0.9)

            rect = Rectangle(
                pos=card.pos,
                size=card.size
            )

        card.bind(
            pos=lambda *_: setattr(rect, "pos", card.pos),
            size=lambda *_: setattr(rect, "size", card.size)
        )

        # =========================================================
        # HEADER
        # =========================================================

        top = BoxLayout(
            size_hint_y=None,
            height=dp_scaled(40)
        )

        title = Label(
            text=f"[b]{plant.get('name', 'Unnamed')}[/b]",
            markup=True,
            font_size=sp_scaled(21),
            halign="left",
            color=(1, 1, 1, 1)
        )

        phase = self._get_current_phase(plant)

        phase_lbl = Label(
            text=phase.upper(),
            size_hint_x=0.35,
            font_size=sp_scaled(18),
            color=self._phase_color(phase)
        )

        top.add_widget(title)
        top.add_widget(phase_lbl)

        card.add_widget(top)

        # =========================================================
        # INFO
        # =========================================================

        info = GridLayout(
            cols=2,
            size_hint_y=None,
            height=dp_scaled(80),
            spacing=dp_scaled(8)
        )

        items = [
            ("STRAIN", plant.get("strain", "---")),
            ("BREEDER", plant.get("breeder", "---")),
            ("MEDIUM", plant.get("medium", "---")),
            ("LIGHT", plant.get("light", "---")),
        ]

        for k, v in items:

            box = BoxLayout(orientation="vertical")

            box.add_widget(Label(
                text=k,
                font_size=sp_scaled(18),
                color=(0.6, 0.6, 0.7, 1)
            ))

            box.add_widget(Label(
                text=str(v),
                font_size=sp_scaled(18),
                color=(1, 1, 1, 1)
            ))

            info.add_widget(box)

        card.add_widget(info)

        # =========================================================
        # DAYS (AUFGESCHLÜSSELT)
        # =========================================================

        # Einzelne Phasen berechnen
        germination_days = self.calc_phase_days(plant, "germination")
        seedling_days = self.calc_phase_days(plant, "seedling")
        veg_days = self.calc_phase_days(plant, "vegetative")
        flower_days = self.calc_phase_days(plant, "flowering")
        
        # Gesamtzeit aus der bestehenden Logik
        total_days = self.calc_total_days(plant)
        
        # Vegi-Zeit kombiniert (Keimung + Sämling + Vegi)
        combined_veg_days = germination_days + seedling_days + veg_days

        # Dreizeiliges Label für die detaillierte Übersicht
        days_text = (
            f"[b]VEGI-ZEIT:[/b] {combined_veg_days} DAYS  |  "
            f"[b]BLÜTEZEIT:[/b] {flower_days} DAYS  |  "
            f"[b]GESAMTZEIT:[/b] {total_days} DAYS"
        )

        days_lbl = Label(
            text=days_text,
            markup=True,
            size_hint_y=None,
            height=dp_scaled(40),
            font_size=sp_scaled(18),
            color=(0.2, 1, 0.4, 1),
            halign="center"
        )

        card.add_widget(days_lbl)

        # =========================================================
        # BUTTONS
        # =========================================================

        btn_box = BoxLayout(
            size_hint_y=None,
            height=dp_scaled(48),
            spacing=dp_scaled(8)
        )

        edit_btn = GlassButton(text="EDIT")
        dup_btn = GlassButton(text="DUPLICATE")
        del_btn = GlassButton(text="DELETE")

        del_btn.color = (1, 0.3, 0.3, 1)

        edit_btn.bind(
            on_release=lambda *_: self.open_edit_popup(plant)
        )

        dup_btn.bind(
            on_release=lambda *_: self.duplicate_plant(plant)
        )

        del_btn.bind(
            on_release=lambda *_: self.delete_plant(plant)
        )

        btn_box.add_widget(edit_btn)
        btn_box.add_widget(dup_btn)
        btn_box.add_widget(del_btn)

        card.add_widget(btn_box)

        return card

    # =============================================================================
    # PHASE
    # =============================================================================

    def _get_current_phase(self, plant):

        today = date.today()

        current = "UNKNOWN"

        for phase in self.PHASES:

            start = plant.get(f"{phase}_start", "")

            if not start:
                continue

            try:
                s = datetime.strptime(
                    start,
                    "%Y-%m-%d"
                ).date()

                if s <= today:
                    current = phase

            except:
                pass

        return current

    def _phase_color(self, phase):

        colors = {
            "germination": (0.4, 0.8, 0.4, 1),
            "seedling": (0.5, 0.9, 0.3, 1),
            "vegetative": (0.2, 0.7, 1, 1),
            "flowering": (0.9, 0.3, 0.9, 1),
            "drying": (1, 0.6, 0.2, 1),
            "curing": (0.8, 0.5, 1, 1)
        }

        return colors.get(
            phase,
            (0.7, 0.7, 0.7, 1)
        )

    # =============================================================================
    # DAYS
    # =============================================================================
# =============================================================================
    # DAYS (KORRIGIERTE LOGIK)
    # =============================================================================

    def calc_phase_days(self, plant, phase):
        """Berechnet die Tage, die eine Pflanze exakt in dieser Phase verbracht hat."""
        start_str = plant.get(f"{phase}_start", "")
        if not start_str:
            return 0
            
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            if start_date > date.today():
                return 0  # Phase hat in der Zukunft noch nicht begonnen

            # Bestimmen, wann diese Phase endet (Start der nächsten Phase)
            end_date = date.today()
            phase_index = self.PHASES.index(phase)
            
            # Suche nach der nächsten Phase, die ein gültiges Startdatum hat
            for next_phase in self.PHASES[phase_index + 1:]:
                next_start_str = plant.get(f"{next_phase}_start", "")
                if next_start_str:
                    try:
                        next_start_date = datetime.strptime(next_start_str, "%Y-%m-%d").date()
                        if next_start_date <= date.today():
                            # Die nächste Phase hat bereits begonnen, also endete die aktuelle Phase am Tag davor
                            end_date = next_start_date
                            break
                    except:
                        pass

            return max(0, (end_date - start_date).days)
        except:
            return 0

    def calc_total_days(self, plant):
        """Berechnet die Gesamtzeit vom allerersten Phasenstart bis heute (oder bis zum Trocknungs-/Curing-Ende)."""
        first_start = None
        for phase in self.PHASES:
            start_str = plant.get(f"{phase}_start", "")
            if start_str:
                try:
                    s = datetime.strptime(start_str, "%Y-%m-%d").date()
                    if s <= date.today():
                        if first_start is None or s < first_start:
                            first_start = s
                except:
                    pass
                    
        if first_start is None:
            return 0
            
        return (date.today() - first_start).days

    # =============================================================================
    # EDIT
    # =============================================================================

    def open_edit_popup(self, plant=None):

        is_new = plant is None

        if is_new:

            plant = {
                "name": "",
                "strain": "",
                "breeder": "",
                "phenotype": "",
                "pot_size": "",
                "medium": "",
                "light": "",
                "location": "",
                "notes": "",
                "tags": "",
                "harvest_weight": "",
                "dry_weight": "",
                "favorite": False,
                "harvest_date": ""
            }

            for phase in self.PHASES:
                plant[f"{phase}_start"] = ""

        self.current_plant = copy.deepcopy(plant)

        popup = Popup(
            title="PLANT EDITOR",
            size_hint=(0.95, 0.95),
            auto_dismiss=False
        )

        root = BoxLayout(
            orientation="vertical",
            spacing=dp_scaled(10),
            padding=dp_scaled(12)
        )

        scroll = ScrollView()

        content = GridLayout(
            cols=1,
            spacing=dp_scaled(10),
            size_hint_y=None
        )

        content.bind(
            minimum_height=content.setter("height")
        )

        fields = [
            ("NAME", "name"),
            ("STRAIN", "strain"),
            ("BREEDER", "breeder"),
            ("PHENOTYPE", "phenotype"),
            ("POT SIZE", "pot_size"),
            ("MEDIUM", "medium"),
            ("LIGHT", "light"),
            ("LOCATION", "location"),
            ("HARVEST WEIGHT", "harvest_weight"),
            ("DRY WEIGHT", "dry_weight"),
            ("TAGS", "tags")
        ]

        for label, key in fields:

            box = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp_scaled(72)
            )

            box.add_widget(Label(
                text=label,
                size_hint_y=None,
                height=dp_scaled(24),
                color=(0.8, 0.8, 0.8, 1)
            ))

            ti = TextInput(
                text=str(
                    self.current_plant.get(key, "")
                ),
                multiline=False,
                background_color=(0.1, 0.1, 0.12, 1),
                foreground_color=(1, 1, 1, 1)
            )

            ti.bind(
                text=lambda inst, val, k=key:
                self.current_plant.update({k: val})
            )

            box.add_widget(ti)

            content.add_widget(box)

        # =========================================================
        # PHASES
        # =========================================================

        for phase in self.PHASES:

            row = BoxLayout(
                size_hint_y=None,
                height=dp_scaled(50),
                spacing=dp_scaled(10)
            )

            lbl = Label(
                text=phase.upper(),
                size_hint_x=0.35
            )

            btn = GlassButton(
                text=self.current_plant.get(
                    f"{phase}_start",
                    "SET DATE"
                )
            )

            def set_date(date_str, ph=phase, b=btn):
                self.current_plant[f"{ph}_start"] = date_str
                b.text = date_str

            btn.bind(
                on_release=lambda *_,
                cb=set_date:
                DatePickerPopup(callback=cb).open()
            )

            row.add_widget(lbl)
            row.add_widget(btn)

            content.add_widget(row)

        # =========================================================
        # NOTES
        # =========================================================

        self.notes_input = TextInput(
            text=self.current_plant.get(
                "notes",
                ""
            ),
            multiline=True,
            size_hint_y=None,
            height=dp_scaled(140),
            background_color=(0.1, 0.1, 0.12, 1),
            foreground_color=(1, 1, 1, 1)
        )

        content.add_widget(self.notes_input)

        scroll.add_widget(content)

        root.add_widget(scroll)

        # =========================================================
        # ACTIONS
        # =========================================================

        actions = BoxLayout(
            size_hint_y=None,
            height=dp_scaled(52),
            spacing=dp_scaled(10)
        )

        cancel_btn = GlassButton(text="CANCEL")
        save_btn = GlassButton(text="SAVE")

        cancel_btn.bind(
            on_release=lambda *_: popup.dismiss()
        )

        save_btn.bind(
            on_release=lambda *_:
            self._save_plant(
                popup,
                is_new,
                plant
            )
        )

        actions.add_widget(cancel_btn)
        actions.add_widget(save_btn)

        root.add_widget(actions)

        popup.content = root
        popup.open()

    # =============================================================================
    # SAVE
    # =============================================================================

    def _save_plant(self, popup, is_new, original):

        self.current_plant["notes"] = (
            self.notes_input.text.strip()
        )

        if is_new:

            self.plants.append(
                copy.deepcopy(self.current_plant)
            )

        else:

            for i, p in enumerate(self.plants):

                if p == original:

                    self.plants[i] = copy.deepcopy(
                        self.current_plant
                    )

                    break

        self._push_plants_to_esp()

        self.build_ui()

        popup.dismiss()

    # =============================================================================
    # DUPLICATE
    # =============================================================================

    def duplicate_plant(self, plant):

        new_plant = copy.deepcopy(plant)

        new_plant["name"] += " COPY"

        self.plants.append(new_plant)

        self._push_plants_to_esp()

        self.build_ui()

    # =============================================================================
    # DELETE
    # =============================================================================

    def delete_plant(self, plant):

        if plant in self.plants:
            self.plants.remove(plant)

        self._push_plants_to_esp()

        self.build_ui()

    # =============================================================================
    # SYNC
    # =============================================================================
    def _check_sync_status(self, dt):
    
        data = GLOBAL_STATE.overlay_engine.get_buffer_data(
            GLOBAL_STATE.get_active_device_id()
        )
    
        if not data:
            return
    
        web_ch = data.get("webserver", {})
    
        pp = web_ch.get("plant_planner", {})
    
        server_rev = int(
            web_ch.get("rev_plant_planner", 0)
        )
    
        if (
            self._last_sent_rev > server_rev and
            (time.time() - self._last_send_time > 3.0)
        ):
    
            if self._retry_count < self._max_retries:
    
                self._retry_count += 1
    
                print(
                    f"[PlantPlanner] WAITING FOR REV CONFIRM "
                    f"{server_rev}/{self._last_sent_rev}"
                )

    def _check_day_rollover(self, dt):
    
        today = date.today()
    
        if today != self._last_day:
    
            self._last_day = today
    
            print(
                "[PlantPlanner] DAY CHANGED -> REFRESH UI"
            )
    
            self.build_ui()
    # =============================================================================
    # UPDATE
    # =============================================================================

    def update_from_global(self, data):
    
        if not data:
            return
    
        self.header.update_from_global(data)
    
        web_ch = data.get("webserver", {})
    
        pp = web_ch.get("plant_planner", {})
    
        if "plants" not in pp:
            return
    
        new_plants = pp["plants"]
    
        if new_plants != self.plants:
    
            self.plants = copy.deepcopy(new_plants)
    
            self.build_ui()