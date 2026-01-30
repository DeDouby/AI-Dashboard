from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
import webbrowser
import sys
import os

class CamPlayerWidget(BoxLayout):
    """
    Player-Widget für Kamera:
    - Öffnet immer den Link im Browser
    - macOS: explizit Safari/Chrome statt VLC
    """

    def __init__(self, **kw):
        super().__init__(**kw)
        self.orientation = "vertical"

        self.label = Label(
            text="📷 Tippe ▶ Start, um Kamera zu starten",
            halign="center",
            valign="middle",
            font_size="20sp"
        )
        self.add_widget(self.label)

    def show_starting(self, url):
        self.label.text = f"🌐 Öffne Kamera im Browser:\n{url}"
        try:
            if sys.platform == "darwin":  # macOS
                # Safari bevorzugt, wenn nicht möglich → Chrome → fallback Default
                for browser_name in ["safari", "chrome"]:
                    try:
                        b = webbrowser.get(browser_name)
                        b.open(url)
                        return
                    except:
                        continue
                webbrowser.open(url)  # fallback
            else:
                webbrowser.open(url)  # Windows / Linux / Android
        except Exception as e:
            self.label.text = f"❌ Fehler beim Öffnen im Browser:\n{e}"

    def show_stopped(self):
        self.label.text = "📷 Kein Live-Stream aktiv."
