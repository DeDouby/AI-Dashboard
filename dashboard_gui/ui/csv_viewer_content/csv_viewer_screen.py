# csv_viewer_screen.py – FINAL, BOTTOM BAR LAYOUT

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button

from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.csv_viewer_content.csv_viewer_filebrowser import CSVViewerFileBrowser
from dashboard_gui.ui.csv_viewer_content.csv_viewer_table import CSVTableView
from dashboard_gui.ui.csv_viewer_content.csv_viewer_graphs import CSVGraphView
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.global_state_manager import GLOBAL_STATE


class CSVViewerScreen(Screen):

    def __init__(self, **kw):
        super().__init__(**kw)
        GLOBAL_STATE.attach_csv_viewer(self)

        self.current_csv = None
        self.active_tab = "Table"

        # ============================================================
        # ROOT
        # ============================================================
        root = BoxLayout(orientation="vertical")
        self.add_widget(root)

        # ============================================================
        # HEADER
        # ============================================================
        self.header = HeaderBar(
            goto_setup=lambda *_: setattr(self.manager, "current", "setup"),
            goto_debug=lambda *_: setattr(self.manager, "current", "debug"),
            goto_device_picker=lambda *_: setattr(self.manager, "current", "device_picker"),
        )
        self.header.lbl_title.text = "CSV Viewer"
        self.header.enable_back("dashboard")
        root.add_widget(self.header)

        # ============================================================
        # CONTENT AREA (EINZIGE!)
        # ============================================================
        self.area = BoxLayout(orientation="vertical")
        root.add_widget(self.area)

        self.table = CSVTableView()
        self.graph = CSVGraphView()

        # ============================================================
        # BOTTOM BAR
        # ============================================================
        bottom = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp_scaled(52),
            spacing=dp_scaled(8),
            padding=[dp_scaled(8), dp_scaled(6)],
        )

        # --- Datei öffnen
        self.btn_open_file = Button(
            text="📁 Datei",
            size_hint=(None, 1),
            width=dp_scaled(110),
            background_down="",
            background_color=(0.20, 0.25, 0.35, 1),
            color=(1, 1, 1, 1),
            font_size=sp_scaled(14),
        )
        self.btn_open_file.bind(on_release=self._open_file)
        bottom.add_widget(self.btn_open_file)

        # --- Tabs
        self.btn_tab_table = Button(
            text="Tabelle",
            background_down="",
            background_color=(0.20, 0.30, 0.70, 1),
            color=(1, 1, 1, 1),
            font_size=sp_scaled(14),
        )
        self.btn_tab_table.bind(on_release=lambda *_: self._switch_tab("Table"))

        self.btn_tab_graph = Button(
            text="Graph",
            background_down="",
            background_color=(0.12, 0.12, 0.18, 1),
            color=(1, 1, 1, 1),
            font_size=sp_scaled(14),
        )
        self.btn_tab_graph.bind(on_release=lambda *_: self._switch_tab("Graph"))

        bottom.add_widget(self.btn_tab_table)
        bottom.add_widget(self.btn_tab_graph)

        # --- Reset (nur Graph)
        self.btn_reset = Button(
            text="Reset",
            size_hint=(None, 1),
            width=dp_scaled(90),
            background_down="",
            background_color=(0.35, 0.20, 0.20, 1),
            color=(1, 1, 1, 1),
            font_size=sp_scaled(14),
        )
        self.btn_reset.bind(on_release=lambda *_: self.graph._reset_view())
        bottom.add_widget(self.btn_reset)

        root.add_widget(bottom)

        # ============================================================
        # START
        # ============================================================
        self._switch_tab("Table")

    # ================================================================
    # FILE BROWSER
    # ================================================================
    def _open_file(self, *_):
        fb = CSVViewerFileBrowser(on_select=self._file_selected)
        self.add_widget(fb)

    def _file_selected(self, path):
        self.current_csv = path
        if self.active_tab == "Table":
            self.table.set_csv_path(path)
        elif self.active_tab == "Graph":
            self.graph.set_csv_path(path)

    # ================================================================
    # TAB SWITCH
    # ================================================================
    def _switch_tab(self, name):
        self.active_tab = name
        self.area.clear_widgets()

        if name == "Table":
            self.btn_tab_table.background_color = (0.20, 0.30, 0.70, 1)
            self.btn_tab_graph.background_color = (0.12, 0.12, 0.18, 1)
            self.btn_reset.opacity = 0
            self.btn_reset.disabled = True

            self.area.add_widget(self.table)
            if self.current_csv:
                self.table.set_csv_path(self.current_csv)

        elif name == "Graph":
            self.btn_tab_graph.background_color = (0.20, 0.30, 0.70, 1)
            self.btn_tab_table.background_color = (0.12, 0.12, 0.18, 1)
            self.btn_reset.opacity = 1
            self.btn_reset.disabled = False

            self.area.add_widget(self.graph)
            if self.current_csv:
                self.graph.set_csv_path(self.current_csv)

    # ================================================================
    # GLOBAL UPDATE
    # ================================================================
    def update_from_global(self, d):
        self.header.update_from_global(d)
