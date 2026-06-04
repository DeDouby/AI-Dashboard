# dashboard_gui/ui/formatters.py
from dashboard_gui.ui.scaling_utils import dp_scaled

class UIFormatter:
    @staticmethod
    def format_sensor_label(name, value, unit, trend="", sz_val=24, sz_trend=24, sz_unit=24, sz_name=24):
        C_SUB = "#bbbbbb"
        
        # WICHTIG: Wir skalieren die Werte HIER für das Markup
        # Wir wandeln in int um, da Markup keine Nachkommastellen bei size mag
        s_sz_name = int(dp_scaled(sz_name))
        s_sz_trend = int(dp_scaled(sz_trend))
        s_sz_val = int(dp_scaled(sz_val))
        s_sz_unit = int(dp_scaled(sz_unit))

        s_name = f"[color={C_SUB}][size={s_sz_name}]{name}[/size][/color]"
        s_trend = f"  [size={s_sz_trend}][font=FA]{trend}[/font][/size]  " if trend else "  "
        
        if isinstance(value, (int, float)):
            s_val = f"[size={s_sz_val}]{value:.2f}[/size]"
        else:
            s_val = f"[size={s_sz_val}]{value}[/size]"
            
        s_unit = f" [color={C_SUB}][size={s_sz_unit}]{unit}[/size][/color]"
        
        return f"{s_name}{s_trend}{s_val}{s_unit}"