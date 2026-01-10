from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.core.window import Window
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
import config
from dashboard_gui.ui.i18n import I18N


class WindowPicker(FloatLayout):
    """
    Globales Menü für Online + Offline Header.
    Ein einziges Modul für ALLE Screens.
    """

    def __init__(
        self,
        parent_header,
        goto_setup,
        goto_debug,
        goto_devices,
        goto_csv,
        goto_settings,
        goto_cam,
        goto_about,
        goto_vpd_scatter,   # <--- NEU
        **kw
    ):
        super().__init__(**kw)

        self.parent_header = parent_header

        bg = Button(background_color=(0, 0, 0, 0))
        bg.bind(on_release=lambda *_: self.close())
        self.add_widget(bg)

        # 5 Einträge (Setup, Settings, Debug, Devices, CSV)
        w = dp_scaled(160)
        h = dp_scaled(5 * 40 + 20)

        self.panel = BoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            size=(w, h),
            spacing=dp_scaled(6),
            pos=(
                Window.width - w - dp_scaled(10),
                Window.height - dp_scaled(50) - h
            )
        )

        dev = config.is_developer_mode()
        
        entries = [
            (I18N.t("menu.vpd_scatter"), goto_vpd_scatter),
            (I18N.t("menu.setup"),       goto_setup),
            (I18N.t("menu.settings"),    goto_settings),
        ]
        
        if dev:
            entries += [
                (I18N.t("menu.debug"),   goto_debug),
                (I18N.t("menu.csv"),     goto_csv),
                (I18N.t("menu.camera"),  goto_cam),
            ]
        
        entries += [
            (I18N.t("menu.devices"),     goto_devices),
            (I18N.t("menu.about"),       goto_about),
        ]

        for label, fnc in entries:
            b = Button(
                text=label,
                font_size=sp_scaled(18),
                background_color=(0.22, 0.25, 0.30, 0.95)
            )
            b.bind(on_release=lambda _, f=fnc: (f(), self.close()))
            self.panel.add_widget(b)

        self.add_widget(self.panel)

    def close(self):
        header = self.parent_header
        screen = header.parent.parent
        if self in screen.children:
            screen.remove_widget(self)

        if hasattr(header, "_menu_overlay") and header._menu_overlay is self:
            header._menu_overlay = None
