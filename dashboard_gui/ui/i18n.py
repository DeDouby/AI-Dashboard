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

            # --- About Screen ---
            "about.version": "ManoVerde Panel 1.24",
            "about.description": (
                "Manoverde is a monitoring and analysis system for Bluetooth Low Energy (BLE) sensors.\n\n"
                "It unifies data from different manufacturers and protocols (ADV, GATT, hybrid devices) "
                "into a single, consistent model.\n\n"
                "Focus is on real-time signals, explicit control, and transparent configuration — "
                "no hidden automations.\n\n"
                "Manoverde interprets devices as they behave, without forcing simplified abstractions.\n\n"
                "Bluetooth is required to detect and read sensors. "
                "Please enable it and grant requested permissions."
            ),
            "about.repo_url": "https://github.com/Hackintosh1980/AI-Dashboard",
            "about.repo_text": "Project & Updates:",
            "about.copyright": "© 2025 Dominik Rosenthal (Hackintosh1980)",
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

            # --- About Screen ---
            "about.version": "Panel ManoVerde 1.24",
            "about.description": (
                "Manoverde es un sistema de monitorización y análisis para sensores "
                "Bluetooth Low Energy (BLE).\n\n"
                "Unifica datos de diferentes fabricantes y protocolos (ADV, GATT, dispositivos híbridos) "
                "en un modelo único y consistente.\n\n"
                "Se centra en señales en tiempo real, control explícito y configuración transparente — "
                "sin automatizaciones ocultas.\n\n"
                "Manoverde interpreta los dispositivos tal como se comportan, "
                "sin forzarlos a abstracciones simplificadas.\n\n"
                "Bluetooth es necesario para detectar y leer los sensores. "
                "Actívalo y concede los permisos solicitados."
            ),
            "about.repo_url": "https://github.com/Hackintosh1980/AI-Dashboard",
            "about.repo_text": "Proyecto y Actualizaciones:",
            "about.copyright": "© 2025 Dominik Rosenthal (Hackintosh1980)",
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

            # --- About Screen ---
            "about.version": "ManoVerde Panel 1.24",
            "about.description": (
                "Manoverde ist ein Überwachungs- und Analysesystem für Bluetooth Low Energy (BLE)-Sensoren.\n\n"
                "Es vereint Daten von verschiedenen Herstellern und Protokollen (ADV, GATT, hybride Geräte) "
                "in einem einheitlichen, konsistenten Modell.\n\n"
                "Fokus liegt auf Echtzeitsignalen, expliziter Steuerung und transparenter Konfiguration — "
                "keine versteckten Automatismen.\n\n"
                "Manoverde interpretiert Geräte so, wie sie sich verhalten, "
                "ohne sie in vereinfachte Abstraktionen zu zwingen.\n\n"
                "Bluetooth ist erforderlich, um Sensoren zu erkennen und auszulesen. "
                "Bitte aktiviere es und gewähre die angeforderten Berechtigungen."
            ),
            "about.repo_url": "https://github.com/Hackintosh1980/AI-Dashboard",
            "about.repo_text": "Projekt & Updates:",
            "about.copyright": "© 2025 Dominik Rosenthal (Hackintosh1980)",
        }
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
