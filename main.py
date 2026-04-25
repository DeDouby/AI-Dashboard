# main.py – EINZIG gültiger Startpunkt (basierend auf main_ui + core)

import os
import sys
from kivy.app import App
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.core.window import Window
from kivy.metrics import dp, sp

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

import core
# main.py (nach GLOBAL_STATE initialisiert)
from dashboard_gui.global_state_manager import GLOBAL_STATE


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
        sm.add_widget(DashboardScreen(name="dashboard"))
        sm.add_widget(SetupScreen(name="setup"))
        sm.add_widget(DebugScreen(name="debug"))
        sm.add_widget(FullScreenView(name="fullscreen"))
        sm.add_widget(DevicePickerScreen(name="device_picker"))
        sm.add_widget(CSVViewerScreen(name="csv_viewer"))
        sm.add_widget(SettingsScreen(name="settings"))
        sm.add_widget(CamViewerScreen(name="cam_viewer"))
        sm.add_widget(AboutScreen(name="about"))
        sm.add_widget(VPDScatterScreen(name="vpd_scatter"))
        sm.add_widget(SensorMixedModeScreen(name="sensor_mixed_mode"))
        sm.add_widget(GrowControllerScreen(name="grow_controller"))
        
        GLOBAL_STATE.bind_screen_manager(sm)
        
        return sm

    # Core starten nach UI-Init
    def on_start(self):
        core.start()

    # Core sauber stoppen
    def on_stop(self):
        core.stop()



    def on_pause(self):
        # nichts tun, nur resident bleiben
        return True

#    def on_resume(self):
#        try:
#            import core
#            print("[APP] resume → bridge restart")
#            core.restart_adv_bridge()
#        except Exception as e:
#            print("[APP] bridge restart failed:", e)

# -------------------------------------------------------
# Offizieller Einstiegspunkt
# -------------------------------------------------------
def main():
    DashboardApp().run()


if __name__ == "__main__":
    main()
