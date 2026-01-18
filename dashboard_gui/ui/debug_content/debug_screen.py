#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import traceback
import config
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.metrics import dp
from kivy.utils import platform
from kivy.uix.screenmanager import Screen
from dashboard_gui.ui.scaling_utils import dp_scaled, sp_scaled
from dashboard_gui.ui.common.header_online import HeaderBar
from dashboard_gui.global_state_manager import GLOBAL_STATE


# ------------------------------------------------------------
# Realpfade
# ------------------------------------------------------------
def get_real_app_paths():
    paths = {}

    data_root = config.DATA

    paths["platform"] = "Android" if platform == "android" else "Desktop"
    paths["data_root"] = data_root

    paths["raw_dump"] = os.path.join(data_root, "ble_dump.json")
    paths["decoded"]  = os.path.join(data_root, "decoded.json")
    paths["config"]   = os.path.join(data_root, "config.json")
    paths["profiles"] = os.path.join(data_root, "decoder_profiles")

    return paths
# ------------------------------------------------------------
# Safe Read
# ------------------------------------------------------------
def safe_read(path, max_len=2500):
    if not os.path.exists(path):
        return "[Datei nicht gefunden]"
    try:
        with open(path, "r", encoding="utf-8") as f:
            txt = f.read(max_len)
        if len(txt) >= max_len:
            txt += "\n… (gekürzt)"
        return txt
    except Exception as e:
        return f"[Fehler beim Lesen: {e}]"


# ------------------------------------------------------------
# DEBUG SCREEN
# ------------------------------------------------------------
class DebugScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)

        root = BoxLayout(orientation="vertical")
        self.add_widget(root)

        # ----------------------------------------------------
        # HEADER (ONLINE, aber standalone – kein State)
        # ----------------------------------------------------
        self.header = HeaderBar()
        self.header.enable_back("dashboard")
        root.add_widget(self.header)
        GLOBAL_STATE.attach_debug(self)

        # ----------------------------------------------------
        # CONTENT
        # ----------------------------------------------------
        scroll = ScrollView(size_hint=(1, 1))
        self.layout = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(12),
            size_hint_y=None,
        )
        self.layout.bind(minimum_height=self._set_min_height)
        scroll.add_widget(self.layout)
        root.add_widget(scroll)

        # ----------------------------------------------------
        # BUTTON-BAR: Refresh – FileManager – Back (ICON STYLE)
        # ----------------------------------------------------
        btn_area = BoxLayout(
            size_hint=(1, None),
            height=dp_scaled(42),
            spacing=dp_scaled(15),
        )
        
        def mk_btn(icon, label, cb, color):
            return Button(
                text=f"[font=FA]{icon}[/font]  {label}",
                markup=True,
                on_release=cb,
                background_normal="",
                background_down="",
                background_color=color,
                color=(1, 1, 1, 1),
                font_size=sp_scaled(18),
                padding=[dp_scaled(12), dp_scaled(8)],
            )
        
        btn_refresh = mk_btn(
            "\uf021",              # refresh
            "Refresh",
            lambda *_: self._build_content(),
            (0.18, 0.35, 0.55, 1)   # Blau – Aktion
        )
        
        btn_file = mk_btn(
            "\uf07c",              # folder
            "Dateien",
            lambda *_: setattr(self.manager, "current", "filemanager"),
            (0.25, 0.25, 0.25, 1)  # Neutral
        )
        
        btn_back = mk_btn(
            "\uf060",              # arrow-left
            "Zurück",
            lambda *_: self._go_back(),
            (0.35, 0.20, 0.20, 1)  # Ruhiges Rot
        )
        
        btn_area.add_widget(btn_refresh)
        btn_area.add_widget(btn_file)
        btn_area.add_widget(btn_back)
        
        root.add_widget(btn_area)
        
        self._build_content()
    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------
    def _add_label(self, text, font_size, bold=False, color=(1, 1, 1, 1), line_height=1.3):
        if bold:
            text = f"[b]{text}[/b]"
    
        lbl = Label(
            text=text,
            markup=True,
            font_size=font_size,
            color=color,
            halign="left",
            valign="top",
            size_hint_y=None,
            line_height=line_height,
        )
    
        # WICHTIG: Textgröße korrekt binden → nichts wird mehr abgeschnitten
        lbl.bind(
            width=lambda inst, w: setattr(inst, "text_size", (w - dp(10), None)),
            texture_size=lambda inst, ts: setattr(inst, "height", ts[1] + dp(8)),
        )
    
        self.layout.add_widget(lbl)
        return lbl

    def _add_separator(self):
        self._add_label("────────────────────────────", dp(11), color=(0.45, 0.45, 0.45, 1))


    def _set_min_height(self, instance, value):
        self.layout.height = value


    # --------------------------------------------------------
    # Content Builder
    # --------------------------------------------------------
    def _build_content(self):
        self.layout.clear_widgets()

        try:
            paths = get_real_app_paths()

            self._add_label("REAL DEBUG – echte Systempfade", dp(20), bold=True)
            self._add_label(f"Plattform: {paths.get('platform')}", dp(14))

            # Fehler anzeigen
            if "error" in paths:
                self._add_label(f"Pfad-Fehler: {paths['error']}", dp(12), color=(1, 0.4, 0.4, 1))
                self._add_separator()

            # SYSTEMPFAD-SEKTION
            self._add_separator()
            self._add_label("Systempfad-Übersicht", dp(18), bold=True)

            for key in ["app_root", "files_dir", "data_root", "raw_dump", "decoded", "config", "profiles"]:
                if key in paths:
                    self._add_label(f"[b]{key}[/b]\n{paths[key]}", dp(13))

            # RAW-DUMP
            self._add_separator()
            self._add_label("ble_dump.json (RAW)", dp(18), bold=True)

            raw = paths.get("raw_dump")
            if raw and os.path.exists(raw):
                self._add_label("✓ Datei existiert", dp(12), color=(0.3, 1, 0.3, 1))
                raw_txt = safe_read(raw, max_len=1200)
                lines = raw_txt.count("\n") + 1
                
                self._add_label(f"{lines} Zeilen", dp(12), color=(0.6, 0.6, 0.6, 1))
                self._add_label(f"[code]{raw_txt}[/code]", dp(11))
            else:
                self._add_label("✗ Datei fehlt", dp(12), color=(1, 0.4, 0.4, 1))
            self._add_label("SYSTEM STATUS", dp(18), bold=True)
            
            ok_color = (0.3, 1, 0.3, 1)
            warn_color = (1, 0.6, 0.2, 1)
            
            def status_line(label, path):
                exists = path and os.path.exists(path)
                self._add_label(
                    f"{'✓' if exists else '✗'} {label}",
                    dp(13),
                    color=ok_color if exists else warn_color
                )
            
            status_line("ble_dump.json", paths.get("raw_dump"))
            status_line("decoded.json", paths.get("decoded"))
            status_line("config.json", paths.get("config"))
            
            self._add_separator()
            # DECODED – SUCHE AN ALLEN ORTEN
            self._add_separator()
            self._add_label("decoded.json", dp(18), bold=True)
            
            p = paths.get("decoded")
            if p and os.path.exists(p):
                self._add_label(f"✓ {p}", dp(12), color=(0.3, 1, 0.3, 1))
                self._add_label(f"[code]{safe_read(p)}[/code]", dp(11))
            else:
                self._add_label(f"✗ {p}", dp(12), color=(1, 0.4, 0.4, 1))

            # CONFIG
            self._add_separator()
            self._add_label("config.json", dp(18), bold=True)

            cfg = paths.get("config")
            if cfg and os.path.exists(cfg):
                self._add_label("✓ Datei existiert", dp(12), color=(0.3, 1, 0.3, 1))
                self._add_label(f"[code]{safe_read(cfg)}[/code]", dp(11))
            else:
                self._add_label("✗ Datei fehlt", dp(12), color=(1, 0.4, 0.4, 1))

            # PROFILE
            self._add_separator()
            self._add_label("Decoder-Profile", dp(18), bold=True)
            prof_dir = paths.get("profiles")

            if prof_dir and os.path.exists(prof_dir):
                files = sorted(os.listdir(prof_dir))
                self._add_label(f"✓ {len(files)} Dateien", dp(12), color=(0.3, 1, 0.3, 1))

                for f in files:
                    fp = os.path.join(prof_dir, f)
                    self._add_label(f"{f}", dp(13), bold=True)
                    self._add_label(f"[code]{safe_read(fp)}[/code]", dp(11))
            else:
                self._add_label("✗ Kein Profilordner", dp(12), color=(1, 0.4, 0.4, 1))

        except Exception:
            self._add_label("[Fehler beim Aufbau]", dp(16), color=(1, 0.4, 0.4, 1), bold=True)
            self._add_label(traceback.format_exc(), dp(11), color=(1, 0.6, 0.6, 1))


    # --------------------------------------------------------
    # Navigation
    # --------------------------------------------------------
    def _go_back(self):
        if self.manager:
            self.manager.current = "dashboard"
    def update_from_global(self, d):
        self.header.update_from_global(d)