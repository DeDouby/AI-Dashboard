# dashboard_gui/device_picker.py
# © 2025 Dominik Rosenthal (Hackintosh1980)

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.metrics import dp

from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.global_state_manager import GLOBAL_STATE


class DevicePickerScreen(Screen):
    name = "device_picker"

    def __init__(self, **kw):
        super().__init__(**kw)
        GLOBAL_STATE.ui_handler.attach_screen("device_picker", self)

        root = BoxLayout(orientation="vertical")

        # -------------------------------------------------
        # HEADER (identisch zu About)
        # -------------------------------------------------
        self.header = HeaderBar()

        self.header.lbl_title.text = "Devices"
        self.header.update_back_button("device_picker")
        root.add_widget(self.header)

        # -------------------------------------------------
        # BODY
        # -------------------------------------------------
        body = BoxLayout(
            orientation="vertical",
            padding=dp_scaled(16),
            spacing=dp_scaled(10)
        )

        scroll = ScrollView()
        body.add_widget(scroll)

        self.list_container = BoxLayout(
            orientation="vertical",
            spacing=dp_scaled(10),
            size_hint_y=None
        )
        self.list_container.bind(
            minimum_height=self.list_container.setter("height")
        )
        scroll.add_widget(self.list_container)

        root.add_widget(body)
        self.add_widget(root)

    # -------------------------------------------------
    # Lifecycle
    # -------------------------------------------------
    def on_pre_enter(self, *_):
        self._build()

    def update_from_global(self, d):
        self.header.update_from_global(d)

    # -------------------------------------------------
    # UI Build
    # -------------------------------------------------
    def _build(self):
        self.list_container.clear_widgets()

        import config
        cfg = config._init()
        devices = cfg.get("devices", {})

        if not devices:
            self.list_container.add_widget(
                Label(text="No devices configured")
            )
            return

        for mac, dev in devices.items():
            self.list_container.add_widget(
                self._device_row(mac, dev)
            )
    # -------------------------------------------------
    # Device Order – swap up / down (CONFIG ONLY)
    # -------------------------------------------------
    def _move_device(self, mac, direction):
        import config

        cfg = config._init()
        devices = cfg.get("devices", {})

        keys = list(devices.keys())
        if mac not in keys:
            return

        idx = keys.index(mac)

        if direction == "up" and idx > 0:
            swap_idx = idx - 1
        elif direction == "down" and idx < len(keys) - 1:
            swap_idx = idx + 1
        else:
            return  # nichts zu tun

        # tauschen
        keys[idx], keys[swap_idx] = keys[swap_idx], keys[idx]

        # neues ordered dict bauen
        new_devices = {k: devices[k] for k in keys}
        cfg["devices"] = new_devices

        config.save(cfg)

        # UI neu aufbauen
        self._build()

    # -------------------------------------------------
    # Adapter für WindowPicker-Kompatibilität
    # -------------------------------------------------
    def open(self):
        if self.manager:
            self.manager.current = self.name

    def _device_row(self, mac, dev):
        box = BoxLayout(
            orientation="vertical",
            padding=[dp_scaled(12), dp_scaled(8)],
            spacing=dp_scaled(6),
            size_hint_y=None
        )
        box.bind(minimum_height=box.setter("height"))

        # Background
        with box.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.18, 0.18, 0.22, 1)
            rect = RoundedRectangle(radius=[dp_scaled(10)], pos=box.pos, size=box.size)

        box.bind(
            pos=lambda *_: setattr(rect, "pos", box.pos),
            size=lambda *_: setattr(rect, "size", box.size)
        )

        # Name input
        name_input = TextInput(
            text=dev.get("name", ""),
            hint_text="Device name",
            multiline=False,
            font_size=sp_scaled(18),
            size_hint_y=None,
            height=dp_scaled(42)
        )

        # MAC label
        mac_lbl = Label(
            text=mac,
            font_size=sp_scaled(14),
            color=(0.7, 0.7, 0.7, 1),
            size_hint_y=None,
            height=dp_scaled(18),
            halign="left"
        )
        mac_lbl.bind(size=lambda *_: mac_lbl.texture_update())

        # Order buttons
        order_row = BoxLayout(
            orientation="horizontal",
            spacing=dp_scaled(8),
            size_hint_y=None,
            height=dp_scaled(36)
        )

        btn_up = Button(
            text="[font=FA]\uf062[/font]",  # arrow-up
            markup=True,
            font_size=sp_scaled(18),
            size_hint=(None, 1),
            width=dp_scaled(44),
            background_down="",
            background_color=(0.25, 0.25, 0.30, 1),
        )
        btn_up.bind(on_release=lambda *_: self._move_device(mac, "up"))
        
        btn_down = Button(
            text="[font=FA]\uf063[/font]",  # arrow-down
            markup=True,
            font_size=sp_scaled(18),
            size_hint=(None, 1),
            width=dp_scaled(44),
            background_down="",
            background_color=(0.25, 0.25, 0.30, 1),
        )
        btn_down.bind(on_release=lambda *_: self._move_device(mac, "down"))
        order_row.add_widget(btn_up)
        order_row.add_widget(btn_down)

        # Save button
        btn = Button(
            text="[font=FA]\uf0c7[/font]  Save",  # floppy-disk
            markup=True,
            font_size=sp_scaled(16),
            size_hint=(None, None),
            size=(dp_scaled(140), dp_scaled(40)),
            background_down="",
            background_color=(0.25, 0.35, 0.30, 1),
        )

        def save_name(*_):
            import config
            cfg = config._init()
            cfg.setdefault("devices", {}).setdefault(mac, {})["name"] = name_input.text.strip()
            config.save(cfg)

        btn.bind(on_release=save_name)

        box.add_widget(name_input)
        box.add_widget(mac_lbl)
        box.add_widget(order_row)
        box.add_widget(btn)


        return box
    def update_from_global(self, d):
        self.header.update_from_global(d)