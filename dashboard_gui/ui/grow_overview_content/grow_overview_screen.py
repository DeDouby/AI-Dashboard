import os

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.graphics import Rectangle, Color

from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.i18n import I18N
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled

from dashboard_gui.ui.grow_overview_content.exhaust_tile import ExhaustTile
from dashboard_gui.ui.grow_overview_content.circulation_tile import CirculationTile
from dashboard_gui.ui.grow_overview_content.light_tile import LightTile
from dashboard_gui.ui.grow_overview_content.esp32_tile import ESP32Tile
from dashboard_gui.global_state_manager import GLOBAL_STATE
from dashboard_gui.ui.grow_overview_content.sensor_internal_sht31_tile import SensorInternalSHT31Tile
from dashboard_gui.ui.grow_overview_content.sensor_external_sht31_tile import SensorExternalSHT31Tile
from dashboard_gui.ui.grow_overview_content.thermobeacon_tile import SensorBLEThermoBeaconTile
from dashboard_gui.ui.grow_overview_content.inkbird_tile import SensorBLEInkbirdTile
from dashboard_gui.ui.grow_overview_content.mlx90614_tile import SensorExternalMLX90614Tile  # ← NEU
from dashboard_gui.ui.grow_overview_content.rtc_tile import RTCTile
ASSET_ROOT = os.path.join("dashboard_gui", "assets")


class GrowOverviewScreen(Screen):

    def __init__(self, **kw):
        super().__init__(**kw)

        GLOBAL_STATE.ui_handler.attach_screen("grow_overview", self)

        # ---------------- ROOT ----------------
        root = BoxLayout(orientation="vertical")

        # ---------------- BACKGROUND ----------------
        with root.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(
                source=os.path.join(ASSET_ROOT, "background_grow_overview.png"),
                pos=root.pos,
                size=root.size
            )

        root.bind(
            pos=lambda *_: setattr(self.bg_rect, "pos", root.pos),
            size=lambda *_: setattr(self.bg_rect, "size", root.size)
        )

        # ---------------- HEADER ----------------
        self.header = HeaderBar()
        self.header.lbl_title.text = I18N.t("menu.grow_overview")
        self.header.update_back_button("grow_overview")
        root.add_widget(self.header)



        # ---------------- CONTENT AREA ----------------
        # Use a horizontal BoxLayout with three columns. Each column
        # contains a header label and a ScrollView holding a vertical
        # BoxLayout so unlimited items can be added.
        from kivy.uix.scrollview import ScrollView

        self.content = BoxLayout(orientation="horizontal", spacing=dp_scaled(2), padding=dp_scaled(2))

        # helper to create a column with header and scroll container
        def make_column(header_text):
            col = BoxLayout(orientation="vertical")
            hdr = Label(
                text=header_text,
                font_size=sp_scaled(20),
                bold=True,
                color=(1, 1, 1, 1),
                size_hint=(1, None),
                height=dp_scaled(48),
                halign="left",
                valign="middle"
            )
            # inner layout holds dynamic children
            inner = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp_scaled(8), padding=[0, dp_scaled(8), 0, dp_scaled(8)])
            inner.bind(minimum_height=inner.setter('height'))

            sv = ScrollView(size_hint=(1, 1))
            sv.add_widget(inner)

            col.add_widget(hdr)
            col.add_widget(sv)
            return col, inner

        # Create three columns
        col1, col1_inner = make_column("GrowMaster S3 Panel")
        col2, col2_inner = make_column("Sensoren")
        col3, col3_inner = make_column("Aktuatoren")

        # keep references so other code can add widgets dynamically
        self.col1_inner = col1_inner
        self.col2_inner = col2_inner
        self.col3_inner = col3_inner

        # ---------------- TILES ----------------
        # ---------------- TILES ----------------
        self.exhaust_tile = ExhaustTile()
        self.circ_tile = CirculationTile()
        self.light_tile = LightTile()
        self.esp32_tile = ESP32Tile()
        
        self.rtc_tile = RTCTile()
        
        self.sht31_internal_tile = SensorInternalSHT31Tile()
        self.sht31_external_tile = SensorExternalSHT31Tile()
        self.thermobeacon_tile = SensorBLEThermoBeaconTile()
        self.inkbird_tile = SensorBLEInkbirdTile()
        self.mlx90614_tile = SensorExternalMLX90614Tile()

        # ---------------- SENSOR SIZE SETTINGS ----------------
        self.sht31_internal_tile.size_hint_y = None
        self.sht31_internal_tile.height = dp_scaled(160)
        self.sht31_internal_tile.size_hint_x = 1
        
        self.sht31_external_tile.size_hint_y = None
        self.sht31_external_tile.height = dp_scaled(160)
        self.sht31_external_tile.size_hint_x = 1
        
        self.thermobeacon_tile.size_hint_y = None
        self.thermobeacon_tile.height = dp_scaled(180)
        self.thermobeacon_tile.size_hint_x = 1
        
        self.inkbird_tile.size_hint_y = None
        self.inkbird_tile.height = dp_scaled(180)
        self.inkbird_tile.size_hint_x = 1
        
        self.mlx90614_tile.size_hint_y = None
        self.mlx90614_tile.height = dp_scaled(160)
        self.mlx90614_tile.size_hint_x = 1

        # Size settings

        # their value box.
        self.exhaust_tile.size_hint_y = None
        self.exhaust_tile.height = dp_scaled(180)
        self.exhaust_tile.size_hint_x = 1

        self.circ_tile.size_hint_y = None
        self.circ_tile.height = dp_scaled(180)
        self.circ_tile.size_hint_x = 1

        self.light_tile.size_hint_y = None
        self.light_tile.height = dp_scaled(200)
        self.light_tile.size_hint_x = 1

        self.rtc_tile.size_hint_y = None
        self.rtc_tile.height = dp_scaled(160)
        self.rtc_tile.size_hint_x = 1
        # ESP32 tile is larger (contains image + value box) so use its
        # internal content height to avoid cropping inside the ScrollView.
        try:
            esp_inner_h = getattr(self.esp32_tile, 'content_container').height
            esp_padding = getattr(self.esp32_tile, 'padding') or 0
            esp_height = esp_inner_h + (esp_padding * 2)
        except Exception:
            esp_height = dp_scaled(520)

        self.esp32_tile.size_hint_y = None
        self.esp32_tile.height = dp_scaled(800)
        self.esp32_tile.size_hint_x = 1

        # Place tiles into appropriate columns
        # Column 1: main panel / device overview
        col1_inner.add_widget(self.esp32_tile)
        col1_inner.add_widget(self.rtc_tile)


        # Column 2: sensors (currently empty by default)
        col2_inner.add_widget(self.sht31_internal_tile) # <--- DAS HAT GEFEHLT!
        col2_inner.add_widget(self.sht31_external_tile) # <--- DAS HAT GEFEHLT!
        col2_inner.add_widget(self.thermobeacon_tile)
        col2_inner.add_widget(self.inkbird_tile)
        col2_inner.add_widget(self.mlx90614_tile)          # ← NEU HIER

        # Column 3: actuators
        col3_inner.add_widget(self.light_tile)
        col3_inner.add_widget(self.circ_tile)
        col3_inner.add_widget(self.exhaust_tile)

        # Add columns to content
        self.content.add_widget(col1)
        self.content.add_widget(col2)
        self.content.add_widget(col3)

        root.add_widget(self.content)
        self.add_widget(root)

    # ---------------- UPDATE ----------------
    # ---------------- UPDATE ----------------
    def update_from_global(self, d):
        self.header.update_from_global(d)

        mac = GLOBAL_STATE.get_active_device_id()
        server_data = GLOBAL_STATE.overlay_engine.get_buffer_data(mac)

        if server_data:
            # 1. Aktivierten Channel aus dem Global State holen
            active_channel = GLOBAL_STATE.get_active_channel() # z.B. "ch1"
            
            # 2. Das exakte Prefix bauen, das auch das DashboardMainPanel nutzt
            # Format: "MAC_CHANNEL" (z.B. "aa:bb:cc:dd:ee:ff_ch1")
            prefix_string = f"{mac}_{active_channel}"

            # 3. Aktuatoren updaten
            self.exhaust_tile.update_values(server_data)
            self.circ_tile.update_values(server_data)
            self.light_tile.update_values(server_data)
            self.esp32_tile.update_values(server_data)
            
            # 4. Sensor-Tiles MIT dem korrekten Prefix versorgen, damit die Trends matchen!
            self.sht31_internal_tile.update_values(server_data, prefix=prefix_string)
            self.sht31_external_tile.update_values(server_data, prefix=prefix_string)
            
            # Falls deine BLE-Tiles (Thermobeacon/Inkbird) intern auch Trends nutzen:
            self.thermobeacon_tile.update_values(server_data, prefix=prefix_string)
            self.inkbird_tile.update_values(server_data, prefix=prefix_string)
            self.mlx90614_tile.update_values(server_data, prefix=prefix_string)   # ← NEU
            self.rtc_tile.update_values(server_data)