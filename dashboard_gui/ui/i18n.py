# -*- coding: utf-8 -*-
"""
I18N Helper – zentrale Übersetzungen
© 2026 Dominik Rosenthal (Hackintosh1980)
"""

import config

class I18N:
    _lang = "en"

    _translations = {
        "en": {
            # Settings
            "settings.title": "Settings",
            "settings.temperature_unit": "Temperature Unit",
            "settings.language": "Language",
            "settings.refresh_interval": "Refresh Interval",
            "settings.ui_refresh_interval": "UI Refresh",
            "settings.stale_timeout": "Stale Timeout",
            "settings.temp_offset": "Temp Offset",
            "settings.humidity_offset": "Humidity Offset",
            "settings.leaf_offset": "Leaf Offset",
            "settings.reset_defaults": "Reset Defaults",
            "settings.save": "Save",
            "settings.cancel": "Cancel",

            # ControlButtons
            "control.start": "Start",
            "control.stop": "Stop",
            "control.reset": "Reset",

            # Window Picker
            "menu.vpd_scatter": "VPD Scatter",
            "menu.setup": "Setup",
            "menu.settings": "Settings",
            "menu.debug": "Debug",
            "menu.csv": "CSV Viewer",
            "menu.camera": "Camera",
            "menu.devices": "Devices",
            "menu.about": "About",
        },

        "es": {
            # Settings
            "settings.title": "Ajustes",
            "settings.temperature_unit": "Unidad de temperatura",
            "settings.language": "Idioma",
            "settings.refresh_interval": "Intervalo de actualización",
            "settings.ui_refresh_interval": "Actualización UI",
            "settings.stale_timeout": "Tiempo de espera",
            "settings.temp_offset": "Offset de temperatura",
            "settings.humidity_offset": "Offset de humedad",
            "settings.leaf_offset": "Offset de hoja",
            "settings.reset_defaults": "Restablecer valores",
            "settings.save": "Guardar",
            "settings.cancel": "Cancelar",

            # ControlButtons
            "control.start": "Iniciar",
            "control.stop": "Detener",
            "control.reset": "Restablecer",

            # Window Picker
            "menu.vpd_scatter": "Dispersión VPD",
            "menu.setup": "Configuración",
            "menu.settings": "Ajustes",
            "menu.debug": "Depuración",
            "menu.csv": "Visor CSV",
            "menu.camera": "Cámara",
            "menu.devices": "Dispositivos",
            "menu.about": "Acerca de",
        },

        "de": {
            # Settings
            "settings.title": "Einstellungen",
            "settings.temperature_unit": "Temperatureinheit",
            "settings.language": "Sprache",
            "settings.refresh_interval": "Aktualisierungsintervall",
            "settings.ui_refresh_interval": "UI-Aktualisierung",
            "settings.stale_timeout": "Inaktivitäts-Timeout",
            "settings.temp_offset": "Temperatur-Korrektur",
            "settings.humidity_offset": "Feuchtigkeit-Korrektur",
            "settings.leaf_offset": "Blatt-Korrektur",
            "settings.reset_defaults": "Standardwerte zurücksetzen",
            "settings.save": "Speichern",
            "settings.cancel": "Abbrechen",

            # ControlButtons
            "control.start": "Start",
            "control.stop": "Stopp",
            "control.reset": "Zurücksetzen",

            # Window Picker
            "menu.vpd_scatter": "VPD-Diagramm",
            "menu.setup": "Setup",
            "menu.settings": "Einstellungen",
            "menu.debug": "Debug",
            "menu.csv": "CSV-Viewer",
            "menu.camera": "Kamera",
            "menu.devices": "Geräte",
            "menu.about": "Über",
        },
    }

    @classmethod
    def init(cls):
        cfg = config._init()
        cls._lang = cfg.get("language", "en")

    @classmethod
    def set_language(cls, lang: str):
        if lang in cls._translations:
            cls._lang = lang

    @classmethod
    def t(cls, key: str, **kwargs):
        text = cls._translations.get(cls._lang, {}).get(key, key)
        if kwargs:
            return text.format(**kwargs)
        return text
