# dashboard_gui/ui/cam_viewer_content/cam_viewer_screen.py

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout

from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.cam_viewer_content.cam_viewer_panel import CamViewerPanel
from dashboard_gui.global_state_manager import GLOBAL_STATE


class CamViewerScreen(Screen):
    """
    Voll integrierter Screen
    """

    def __init__(self, **kw):
        super().__init__(**kw)
        GLOBAL_STATE.attach_cam_viewer(self)

        root = BoxLayout(orientation="vertical")

        # HEADER
        self.header = HeaderBar()

        self.header.update_back_button("cam_viewer")
        
        root.add_widget(self.header)

        # PANEL
        panel = CamViewerPanel()
        root.add_widget(panel)

        self.add_widget(root)

    def update_from_global(self, d):
        self.header.update_from_global(d)        
