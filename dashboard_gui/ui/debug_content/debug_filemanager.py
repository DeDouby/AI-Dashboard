#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from kivy.utils import platform

# ------------------------------------------------------------
# Root bestimmen (gleich wie im Debug-Screen)
# ------------------------------------------------------------
def get_data_root():
    if platform == "android":
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        ctx = PythonActivity.mActivity
        files = ctx.getFilesDir().getAbsolutePath()
        return os.path.join(files, "app", "data")
    else:
        base = os.path.dirname(os.path.abspath(__file__))
        return os.path.abspath(os.path.join(base, "..", "data"))

# ------------------------------------------------------------
# Einfaches, sicheres Lesen
# ------------------------------------------------------------
def safe_read(path, max_len=5000):
    if not os.path.exists(path):
        return "[Datei nicht gefunden]"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read(max_len)
    except Exception as e:
        return f"[Fehler: {e}]"


# ------------------------------------------------------------
# FILE MANAGER SCREEN
# ------------------------------------------------------------
class DebugFileManagerScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.current_path = get_data_root()

        root = BoxLayout(orientation="vertical", spacing=5)
        self.add_widget(root)

        # Titel
        self.lbl_title = Label(
            text=f"[b]Datei Browser[/b]\n{self.current_path}",
            markup=True, font_size=dp(20), size_hint=(1, None), height=dp(70)
        )
        root.add_widget(self.lbl_title)

        # Scrollbereich
        self.scroll = ScrollView()
        self.list_layout = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=8,
            padding=10
        )
        self.list_layout.bind(minimum_height=lambda inst, h: setattr(self.list_layout, "height", h))
        self.scroll.add_widget(self.list_layout)
        root.add_widget(self.scroll)

        # Button-Bereich
        btns = BoxLayout(size_hint=(1, None), height=dp(60), spacing=20)
        btns.add_widget(Button(text="↩ Zurück", on_release=lambda *_: self._go_back()))
        btns.add_widget(Button(text="⬆ Hoch", on_release=lambda *_: self._go_up()))
        root.add_widget(btns)

        self.refresh()

    # --------------------------------------------------------
    # Navigation
    # --------------------------------------------------------
    def _go_back(self):
        if self.manager:
            self.manager.current = "debug"

    def _go_up(self):
        parent = os.path.dirname(self.current_path)
        data_root = get_data_root()
        if len(parent) >= len(data_root):
            self.current_path = parent
            self.refresh()

    # --------------------------------------------------------
    # Directory neu laden
    # --------------------------------------------------------
    def refresh(self):
        self.lbl_title.text = f"[b]Datei Browser[/b]\n{self.current_path}"
        self.list_layout.clear_widgets()

        try:
            entries = sorted(os.listdir(self.current_path))
        except Exception as e:
            self.list_layout.add_widget(Label(text=f"[Fehler: {e}]"))
            return

        for name in entries:
            full = os.path.join(self.current_path, name)

            if os.path.isdir(full):
                btn = Button(
                    text=f"📁 {name}",
                    size_hint_y=None,
                    height=dp(48),
                    on_release=lambda _, p=full: self._enter(p)
                )
                self.list_layout.add_widget(btn)

            else:
                btn = Button(
                    text=f"📄 {name}",
                    size_hint_y=None,
                    height=dp(48),
                    on_release=lambda _, p=full: self._show_file(p)
                )
                self.list_layout.add_widget(btn)

    # --------------------------------------------------------
    # Ordner öffnen
    # --------------------------------------------------------
    def _enter(self, path):
        self.current_path = path
        self.refresh()

    # --------------------------------------------------------
    # Datei anzeigen
    # --------------------------------------------------------
    def _show_file(self, path):
        text = safe_read(path)

        popup = ScrollView(size_hint=(1, 0.9))
        layout = BoxLayout(orientation="vertical", size_hint_y=None, padding=10)
        layout.bind(minimum_height=lambda inst, h: setattr(layout, "height", h))
        popup.add_widget(layout)

        layout.add_widget(Label(
            text=f"[b]{os.path.basename(path)}[/b]\n\n[code]{text}[/code]",
            markup=True,
            font_size=dp(16),
            size_hint_y=None
        ))

        close = Button(text="Schließen", size_hint_y=None, height=dp(50))
        close.bind(on_release=lambda *_: self.remove_widget(popup))
        layout.add_widget(close)

        self.add_widget(popup)
