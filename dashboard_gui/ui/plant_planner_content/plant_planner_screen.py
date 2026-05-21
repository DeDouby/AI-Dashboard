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
        self.font_size = sp_scaled(13)

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

class DatePickerPopup(Popup):

    selected_date = StringProperty("")

    def __init__(self, callback=None, **kwargs):
        super().__init__(**kwargs)

        self.callback = callback

        self.title = "SELECT DATE"
        self.size_hint = (0.92, 0.85)
        self.auto_dismiss = False

        root = BoxLayout(
            orientation="vertical",
            padding=dp_scaled(15),
            spacing=dp_scaled(10)
        )

        self.days_grid = GridLayout(
            cols=7,
            spacing=dp_scaled(4)
        )

        for d in range(1, 32):
            btn = ToggleButton(
                text=str(d),
                group="date_picker",
                size_hint_y=None,
                height=dp_scaled(48),
                background_color=(0.15, 0.15, 0.2, 1)
            )

            btn.bind(on_release=self._select_day)

            self.days_grid.add_widget(btn)

        scroll = ScrollView()
        scroll.add_widget(self.days_grid)

        root.add_widget(scroll)

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

        root.add_widget(btn_box)

        self.content = root

    def _select_day(self, btn):
        today = date.today()

        self.selected_date = (
            f"{today.year}-{today.month:02d}-{int(btn.text):02d}"
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
            font_size=sp_scaled(15)
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

    def build_ui(self):

        self.body.clear_widgets()

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

        for plant in filtered:
            self.body.add_widget(
                self._build_plant_card(plant)
            )

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

        card.height = dp_scaled(220)

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
            font_size=sp_scaled(15),
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
                font_size=sp_scaled(11),
                color=(0.6, 0.6, 0.7, 1)
            ))

            box.add_widget(Label(
                text=str(v),
                font_size=sp_scaled(14),
                color=(1, 1, 1, 1)
            ))

            info.add_widget(box)

        card.add_widget(info)

        # =========================================================
        # DAYS
        # =========================================================

        days = self.calc_total_days(plant)

        days_lbl = Label(
            text=f"[b]{days} DAYS TOTAL[/b]",
            markup=True,
            size_hint_y=None,
            height=dp_scaled(32),
            font_size=sp_scaled(16),
            color=(0.2, 1, 0.4, 1)
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

    def calc_total_days(self, plant):

        total = 0

        for phase in self.PHASES:

            start = plant.get(f"{phase}_start", "")

            if not start:
                continue

            try:
                s = datetime.strptime(
                    start,
                    "%Y-%m-%d"
                ).date()

                total = max(
                    total,
                    (date.today() - s).days
                )

            except:
                pass

        return total

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
                plant[f"{phase}_end"] = ""

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

        pp = data.get("plant_planner", {})

        server_rev = int(
            pp.get("rev_plant_planner", 0)
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

    # =============================================================================
    # UPDATE
    # =============================================================================

    def update_from_global(self, data):

        if not data:
            return

        self.header.update_from_global(data)

        pp = data.get("plant_planner", {})

        if "plants" not in pp:
            return
        
        new_plants = pp["plants"]
        
        if new_plants != self.plants:
        
            self.plants = copy.deepcopy(new_plants)
        
            self.build_ui()