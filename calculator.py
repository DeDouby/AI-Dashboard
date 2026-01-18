# calculator.py – universal & minimal
# © 2025 Dominik Rosenthal

import math
import config

# ------------------------------------------------------------
# Überprüfen ob externer Sensor vorhanden ist
# (Decoder benötigt diese Funktion → NICHT entfernen!)
# ------------------------------------------------------------
def external_present(humidity_external):
    if humidity_external is None:
        return False
    # ThermoBeacon-Logik
    return not (humidity_external <= 0.1 or humidity_external > 110.0)


# ------------------------------------------------------------
# Offsets korrekt anwenden – GLOBAL (intern + extern)
# None bleibt None → KEINE Logik
# ------------------------------------------------------------
def apply_offsets(T_i, H_i, T_e, H_e):

    temp_off = config.get_temperature_offset()
    hum_off  = config.get_humidity_offset()

    if T_i is not None:
        T_i = T_i + temp_off
    if H_i is not None:
        H_i = H_i + hum_off

    if T_e is not None:
        T_e = T_e + temp_off
    if H_e is not None:
        H_e = H_e + hum_off

    return T_i, H_i, T_e, H_e


# ------------------------------------------------------------
# Einheit anwenden (C/F)
# ------------------------------------------------------------
def to_unit(temp_c):
    if temp_c is None:
        return None
    unit = config.get_temperature_unit().upper()
    if unit == "F":
        return temp_c * 9/5 + 32
    return temp_c


# ------------------------------------------------------------
# VPD (kPa)
# ------------------------------------------------------------
def _vpd(temp_c, rh):
    if temp_c is None or rh is None:
        return None
    svp = 610.78 * math.exp((17.269 * temp_c) / (temp_c + 237.3))
    avp = svp * (rh / 100.0)
    return round((svp - avp) / 1000.0, 3)


def vpd_internal(T_i, H_i):
    if T_i is None or H_i is None:
        return None
    leaf_off = config.get_leaf_offset()
    return _vpd(T_i + leaf_off, H_i)


def vpd_external(T_e, H_e):
    if T_e is None or H_e is None:
        return None
    leaf_off = config.get_leaf_offset()
    return _vpd(T_e + leaf_off, H_e)

# ------------------------------------------------------------
# Scatter-Koordinaten (einheitenfrei)
# x = humidity (%)
# y = temperature (°C, inkl. leaf offset!)
# ------------------------------------------------------------
def vpd_coord_internal(T_i, H_i):
    if T_i is None or H_i is None:
        return None, None
    leaf_off = config.get_leaf_offset()
    return H_i, T_i + leaf_off


def vpd_coord_external(T_e, H_e):
    if T_e is None or H_e is None:
        return None, None
    leaf_off = config.get_leaf_offset()
    return H_e, T_e + leaf_off
