# dashboard_gui/ui/cam_viewer_content/cam_player_widget.py

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.utils import platform
import webbrowser

class CamPlayerWidget(BoxLayout):
    """
    Desktop:
        - Kein eigenes Video, ffplay öffnet extern
        - Hier im Panel nur Text "Live wird extern angezeigt"

    Android:
        - Öffnet die angegebene Kamera-Adresse direkt im Browser
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
        if platform == "android":
            self.label.text = f"Öffne Kamera im Browser:\n{url}"
            try:
                webbrowser.open(url)
            except Exception as e:
                self.label.text = f"❌ Fehler beim Öffnen im Browser:\n{e}"
        else:
            self.label.text = f"▶ Live-Stream startet im externen Fenster (ffplay)\n{url}"

    def show_stopped(self):
        if platform == "android":
            self.label.text = "📷 Kein Live-Stream aktiv."
        else:
            self.label.text = "Live-Stream gestoppt."