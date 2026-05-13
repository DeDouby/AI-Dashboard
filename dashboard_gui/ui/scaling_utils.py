# -------------------------------------------------------
# 🔧 UI SCALING FIX (STABIL FÜR DESKTOP + ANDROID)
# -------------------------------------------------------
import sys
from kivy.core.window import Window
from kivy.utils import platform
from kivy.metrics import dp, sp


def compute_ui_scale():
    w, h = Window.size
    # Wir holen uns die echte physikalische Dichte
    # Aber Vorsicht: Manche Phones lügen hier!
    dpi = Window.dpi if Window.dpi and Window.dpi > 100 else 160
    short_side = min(w, h)

    if platform not in ("android", "ios"):
        return 1.15 * max(0.95, min(w / 1400.0, 1.10))

    # --- DIE RADIKAL-WEICHE ---
    
    # 1. Check: Ist es ein High-Res Display wie das Huawei?
    # Wenn die kurze Seite >= 1080px ist UND die DPI hoch ist
    if short_side >= 1080 or dpi > 350:
        # Hier schalten wir fast alle Faktoren aus. 
        # 0.55 - 0.60 ist oft der "Sweet Spot" für FHD Geräte,
        # damit die Widgets nicht den Screen sprengen.
        return 0.58 

    # 2. Check: Das Nokia/Redmi Profil (HD+)
    # Das hat ja bei dir "Geil" ausgesehen.
    # Wir nehmen den Wert, der beim Nokia funktionierte:
    base = 0.78
    geom = short_side / 720.0
    density_boost = max(1.0, min(400.0 / dpi, 1.10))
    
    return base * geom * density_boost


# 🔥 GLOBAL SCALE (nur 1x berechnet!)
UI_SCALE = compute_ui_scale()


# -------------------------------------------------------
# 📏 SCALED HELPERS (einzige Quelle!)
# -------------------------------------------------------
def dp_scaled(v: float) -> float:
    return dp(v * UI_SCALE)


def sp_scaled(v: float) -> float:
    return sp(v * UI_SCALE)