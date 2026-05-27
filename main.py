# main.py – EINZIG gültiger Startpunkt (basierend auf main_ui + core)

import os
import sys
from kivy.app import App
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.clock import Clock
# -------------------------------------------------------
# Screens & Logik-Module
# -------------------------------------------------------
from dashboard_gui.dashboard import DashboardScreen
from dashboard_gui.setup_screen import SetupScreen
from dashboard_gui.ui.debug_content.debug_screen import DebugScreen
from dashboard_gui.data_buffer import BUFFER
from dashboard_gui.ui.fullscreen_content.fullscreen_view import FullScreenView
from dashboard_gui.ui.device_picker_content.device_picker import DevicePickerScreen
from dashboard_gui.ui.csv_viewer_content.csv_viewer_screen import CSVViewerScreen
from dashboard_gui.settings_screen import SettingsScreen
from dashboard_gui.ui.cam_viewer_content.cam_viewer_screen import CamViewerScreen
from dashboard_gui.ui.about_content.about_screen import AboutScreen
from dashboard_gui.ui.vpd_scatter_screen_content.vpd_scatter_screen import VPDScatterScreen
from dashboard_gui.ui.sensor_mixed_mode_content.sensor_mixed_mode_screen import SensorMixedModeScreen
from dashboard_gui.ui.grow_controller_content.grow_controller_screen import GrowControllerScreen
from dashboard_gui.ui.i18n import I18N
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.plant_planner_content.plant_planner_screen import PlantPlannerScreen
from dashboard_gui.ui.grow_overview_content.grow_overview_screen import GrowOverviewScreen
import core
# main.py (nach GLOBAL_STATE initialisiert)
from dashboard_gui.global_state_manager import GLOBAL_STATE
from kivy.config import Config
Config.set('graphics', 'multisamples', '0')      # Weniger GPU-Last
Config.set('kivy', 'default_font', 'Roboto')     # Falls möglich

# -------------------------------------------------------
# FontAwesome sicher laden
# -------------------------------------------------------
FONT_PATH = os.path.join(
    os.path.dirname(__file__),
    "dashboard_gui", "assets", "fonts", "fa-solid-900.ttf"
)

if os.path.exists(FONT_PATH):
    LabelBase.register(name="FA", fn_regular=FONT_PATH)
else:
    print("⚠️ Font fehlt:", FONT_PATH)


# -------------------------------------------------------
# Buffer vor UI initialisieren
# -------------------------------------------------------
def init_buffer():
    BUFFER.load()
    if not BUFFER.data or not isinstance(BUFFER.data, list):
        BUFFER.data = []
    BUFFER.file_exists = True
    BUFFER.data_ok = True
    BUFFER.alive_flag = True


# -------------------------------------------------------
# Haupt-App (UI + Core)
# -------------------------------------------------------
class DashboardApp(App):

    def build(self):
        I18N.init()
        init_buffer()

        sm = ScreenManager(transition=FadeTransition())

        # === Nur essenzielle Screens sofort laden ===
        sm.add_widget(DashboardScreen(name="dashboard"))
        sm.add_widget(SetupScreen(name="setup"))
        sm.add_widget(DebugScreen(name="debug"))
        sm.add_widget(GrowOverviewScreen(name="grow_overview"))
        # Rest lazy laden
        self.screen_manager = sm
        GLOBAL_STATE.bind_screen_manager(sm)

        return sm

    # Core starten nach UI-Init
    def on_start(self):
        core.start()
        Clock.schedule_once(self._lazy_load_screens, 0.8)

    def _lazy_load_screens(self, dt):
        """Schwere Screens erst nach dem ersten Frame laden"""
        print("[LAZY] Lade zusätzliche Screens...")

        screens_to_load = {
            "fullscreen": "dashboard_gui.ui.fullscreen_content.fullscreen_view:FullScreenView",
            "device_picker": "dashboard_gui.ui.device_picker_content.device_picker:DevicePickerScreen",
            "csv_viewer": "dashboard_gui.ui.csv_viewer_content.csv_viewer_screen:CSVViewerScreen",
            "settings": "dashboard_gui.settings_screen:SettingsScreen",
            "cam_viewer": "dashboard_gui.ui.cam_viewer_content.cam_viewer_screen:CamViewerScreen",
            "about": "dashboard_gui.ui.about_content.about_screen:AboutScreen",
            "vpd_scatter": "dashboard_gui.ui.vpd_scatter_screen_content.vpd_scatter_screen:VPDScatterScreen",
            "sensor_mixed_mode": "dashboard_gui.ui.sensor_mixed_mode_content.sensor_mixed_mode_screen:SensorMixedModeScreen",
            "grow_controller": "dashboard_gui.ui.grow_controller_content.grow_controller_screen:GrowControllerScreen",
            "plant_planner": "dashboard_gui.ui.plant_planner_content.plant_planner_screen:PlantPlannerScreen",
        }

        for name, import_path in screens_to_load.items():
            try:
                module_path, class_name = import_path.split(':')
                module = __import__(module_path, fromlist=[class_name])
                ScreenClass = getattr(module, class_name)
                
                screen = ScreenClass(name=name)
                self.screen_manager.add_widget(screen)
                print(f"[LAZY] ✓ {name} geladen")
            except Exception as e:
                print(f"[LAZY] ✗ Fehler beim Laden von {name}: {e}")

    def on_stop(self):
        core.stop()        
    # Core sauber stoppen
    def on_stop(self):
        core.stop()



    def on_pause(self):
        # nichts tun, nur resident bleiben
        return True

    def on_resume(self):
        print("[APP] RESUME")
    
        Clock.schedule_once(self._rebuild_dashboard_graphs, 0.5)
    
        return True
    
    def _rebuild_dashboard_graphs(self, dt):
        try:
            dashboard = self.root.get_screen("dashboard")
    
            for tile in dashboard.content.tile_map.values():
                tile.rebuild_graph()
    
        except Exception as e:
            print("[RESUME ERROR]", e)

# -------------------------------------------------------
# Offizieller Einstiegspunkt
# -------------------------------------------------------
def main():
    DashboardApp().run()


if __name__ == "__main__":
    main()
