# -------------------------------------------------------
# 🔧 UI SCALING FIX (STABIL FÜR DESKTOP + ANDROID)
# -------------------------------------------------------
import sys
from kivy.core.window import Window
from kivy.utils import platform
from kivy.metrics import dp, sp


def compute_ui_scale():
    w, h = Window.size

    # DPI SAFE FALLBACK (wichtig für Android!)
    dpi = Window.dpi
    if not dpi or dpi < 100:
        dpi = 160

    # ---------------------------------------------------
    # 🖥️ DESKTOP
    # ---------------------------------------------------
    if platform not in ("android", "ios"):
        base = 1.15
        geom = w / 1400.0
        geom = max(0.95, min(geom, 1.10))
        return base * geom

    # ---------------------------------------------------
    # 📱 ANDROID
    # ---------------------------------------------------
    density = dpi / 420.0
    density = max(0.85, min(density, 1.15))

    geom = w / 1080.0
    geom = max(0.85, min(geom, 1.0))

    return 0.75 * density * geom


# 🔥 GLOBAL SCALE (nur 1x berechnet!)
UI_SCALE = compute_ui_scale()


# -------------------------------------------------------
# 📏 SCALED HELPERS (einzige Quelle!)
# -------------------------------------------------------
def dp_scaled(v: float) -> float:
    return dp(v * UI_SCALE)


def sp_scaled(v: float) -> float:
    return sp(v * UI_SCALE)