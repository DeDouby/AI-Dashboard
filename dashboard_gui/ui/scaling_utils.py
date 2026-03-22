import sys
from kivy.config import Config

# -------------------------------------------------------
# 🖥️ DESKTOP INITIALISIERUNG (VOR ALLEM ANDEREN)
# -------------------------------------------------------
if sys.platform not in ("android", "ios"):
    # Wir setzen die Werte direkt in die Kivy-Config, 
    # damit sie beim Erstellen des Fensters bereits existieren.
    Config.set('graphics', 'width', '1400')
    Config.set('graphics', 'height', '800')
    Config.set('graphics', 'minimum_width', '900')
    Config.set('graphics', 'minimum_height', '600')
    # Das hier verhindert, dass das Fenster beim Starten flackert:
    Config.set('graphics', 'resizable', '1') 
    Config.write() # Schreibt es intern fest für diesen Run

# Erst JETZT die anderen Kivy-Sachen importieren
from kivy.core.window import Window
from kivy.metrics import dp, sp
# -------------------------------------------------------
# 🔧 Global UI scale berechnet aus Window DPI/Size
# -------------------------------------------------------
def compute_ui_scale():
    import sys

    try:
        w, h = Window.size
        dpi = Window.dpi or 96.0
    except Exception:
        w, h, dpi = 1400.0, 800.0, 96.0

    # ---------------------------------------------------
    # 🖥️ DESKTOP
    # ---------------------------------------------------
    if sys.platform not in ("android", "ios"):
        # Baseline: Desktop ist ergonomisch größer nötig
        BASE = 1.2 # <<< sweet spot: 1.08 – 1.18

        # Breiten-Kompensation
        geom = w / 1400.0
        geom = max(0.90, min(geom, 1.10))

        return BASE * geom

    # ---------------------------------------------------
    # 📱 ANDROID / iOS
    # ---------------------------------------------------
    BASE = 0.72

    density_factor = dpi / 420.0
    density_factor = max(0.85, min(density_factor, 1.1))

    geom_factor = min(w / 1080.0, 1.0)
    geom_factor = max(0.85, geom_factor)

    raw = BASE * density_factor * geom_factor
    return max(0.70, min(raw, 0.90))


UI_SCALE = compute_ui_scale()

import sys
from kivy.metrics import dp, sp

def dp_scaled(v: float) -> float:
    return dp(v * UI_SCALE)

def sp_scaled(v: float) -> float:
    text_boost = 1.05 if sys.platform not in ("android", "ios") else 1.0
    return sp(v * UI_SCALE * text_boost)
