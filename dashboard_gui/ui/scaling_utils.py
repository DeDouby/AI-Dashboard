import sys
from kivy.core.window import Window
from kivy.utils import platform
from kivy.metrics import dp, sp

def compute_ui_scale():
    # Basisdaten erfassen
    w, h = Window.size
    dpi = Window.dpi if Window.dpi and Window.dpi > 100 else 160
    short_side = min(w, h)
    long_side = max(w, h)
    
    # 0. Sicherheitscheck: Desktop / Tablet Umgebungen
    if platform not in ("android", "ios"):
        return 1.15 * max(0.95, min(w / 1400.0, 1.10))

    # 1. High-Res / High-DPI Schutz (Huawei etc.)
    # Hier greifen wir nicht ein, das passt bereits.
    if short_side >= 1080 or dpi > 350:
        return 0.58 

    # 2. Dynamische Ratio-Korrektur (Fix für Redmi 10c & Co.)
    # Wir berechnen das Seitenverhältnis. Je schmaler/länger das Gerät,
    # desto stärker müssen wir den Scale begrenzen, damit die 500dp Höhe passen.
    aspect = long_side / short_side
    
    # Basis-Geometrie auf Basis der 720px Breite (wie gehabt)
    base_geom = short_side / 720.0
    density_boost = max(1.0, min(400.0 / dpi, 1.10))
    raw_scale = base_geom * density_boost
    
    # Wir wenden hier den "Deckel" an:
    # Je extremer das Format, desto niedriger der max. erlaubte Scale-Faktor.
    if aspect > 2.1:
        # Sehr schmal (Redmi 10c Kategorie) -> Aggressives Shrinking
        return min(raw_scale, 0.72)
    elif aspect > 1.9:
        # Mittlere Schmalheit (Nokia Bereich) -> Moderates Shrinking
        return min(raw_scale, 0.82)
    
    # Standard-Verhalten für normale Verhältnisse (1.6 bis 1.9)
    return raw_scale * 0.78

# 🔥 GLOBAL SCALE (wird einmalig beim App-Start berechnet)
UI_SCALE = compute_ui_scale()

# -------------------------------------------------------
# 📏 SCALED HELPERS (einzige Quelle!)
# -------------------------------------------------------
def dp_scaled(v: float) -> float:
    return dp(v * UI_SCALE)

def sp_scaled(v: float) -> float:
    return sp(v * UI_SCALE)