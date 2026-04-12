#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###############################################################################
# !!! ABSOLUTES GESETZ v2.0: HYBRIDE STABILITÄT & RAM-DOMINANZ !!!
# -----------------------------------------------------------------------------
# 0. SINGLE SOURCE OF TRUTH (DIE QUELLE)
#    Der Decoder ist der alleinige Herrscher über den Systemstatus. 
#    UI und Engines lesen NUR die 'decoded.json'. Der Decoder liest für WEB
#    direkt aus dem RAM (_LIVE_WEB_DATA) – die Festplatte ist für WEB-Validierung tot.
#
# -----------------------------------------------------------------------------
# 1. RAM-INJEKTION VOR DISK-I/O
#    Web-Daten fließen per Direkt-Injektion in den Arbeitsspeicher. 
#    Ein langsames Dateisystem (SD-Karte/Android-I/O) darf niemals die 
#    Aktualität der Daten bremsen oder Flackern verursachen.
#
# -----------------------------------------------------------------------------
# 2. AUTONOME TIMEOUT-HOHEIT (DAS ENDE DES FLACKERNS)
#    Der Decoder berechnet den Offline-Status für WEB-Geräte SELBSTSTÄNDIG:
#    (Aktuelle_Zeit - Paket_Zeitstempel) > config.stale_timeout.
#    Der externe Watchdog-Status wird für WEB ignoriert, um Fehlalarme 
#    durch Netzwerk-Latenz zu eliminieren.
#
# -----------------------------------------------------------------------------
# 3. KANAL-ISOLATION & GNADENFRIST
#    Ein stockender Web-Request darf weder die BLE-Daten (ADV/GATT) stören, 
#    noch das Gerät sofort auf "offline" reißen. Solange der Cache innerhalb 
#    der Config-Zeit liegt, bleibt der Status "active".
#
# -----------------------------------------------------------------------------
# 4. LAST-GOOD-DATA (KEIN DATENVAKUUM)
#    Bei einem misslungenen Request oder korrupten Paket wird zwingend der 
#    letzte gültige Stand aus dem RAM-Cache serviert. "Leere" Frames 
#    zwischen zwei erfolgreichen Updates sind streng verboten.
#
# -----------------------------------------------------------------------------
# 5. ATOMARE KONSISTENZ
#    Die 'decoded.json' wird nur geschrieben, wenn der Frame in sich logisch ist.
#    Mischmasch aus uralten Web-Daten und frischen BLE-Daten wird durch 
#    individuelle Zeitstempel pro Kanal innerhalb des Objekts verhindert.
#
# -----------------------------------------------------------------------------
# 6. VERBOTENE MUSTER (TODSÜNDEN)
#    ❌ Watchdog sagt "offline" -> sofortiges Ausgrauen in der UI (WEB-Kanal)
#    ❌ config.stale_timeout ignorieren oder hartcodieren
#    ❌ Direktes Lesen der web_dump.json für die Status-Logik
#
# -----------------------------------------------------------------------------
# 7. ERLAUBTE MUSTER (GOLD STANDARD)
#    ✅ RAM-Cache (_LAST_WEB) als primäre Validierung
#    ✅ 'now - timestamp' gegen Config-Wert prüfen
#    ✅ Den Watchdog nur noch für passive Kanäle (BLE) als Berater nutzen
#
###############################################################################
import os, json, time, threading, csv
from kivy.utils import platform
import config
import calculator

# ------------------------------------------------------------
# PFAD-LOGIK
# ------------------------------------------------------------
BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")

if platform == "android":
    from jnius import autoclass
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    ctx = PythonActivity.mActivity

    DATA = os.path.join(ctx.getFilesDir().getAbsolutePath(), "app", "data")
else:
    BASE = os.path.dirname(os.path.abspath(__file__))
    DATA = os.path.join(BASE, "data")

RAW_FILE = os.path.join(DATA, "ble_dump.json")
DEC_FILE = os.path.join(DATA, "decoded.json")
PROFILES = os.path.join(DATA, "decoder_profiles")
CSV_FILE = os.path.join(DATA, "log.csv")

os.makedirs(DATA, exist_ok=True)
os.makedirs(PROFILES, exist_ok=True)

BRIDGE_ALIVE = True
BRIDGE_STATUS = "OK"
BRIDGE_LAST_SEEN = None
UPTIME_START = None

# Stale-Handling pro Kanal
_LAST_ADV_RAW = {}
_LAST_ADV_TS = {}

_LAST_GATT_RAW = {}
_LAST_GATT_TS = {}
_LAST_WEB = {}
_LAST_WRITE_TS = 0
_WRITE_INTERVAL = 1.0  # oder 0.5 testen
_LAST_HASH = None
# 🔥 NEU: Zentrale RAM-Quelle für ALLES
_DECODED_RAM = []
_DECODED_TS = 0
# ------------------------------------------------------------
# LOG-THROTTLE (HART AUF 60 SEKUNDEN)
# ------------------------------------------------------------
_LAST_LOG_TS = 0.0
_LOG_INTERVAL = 60.0  # HARDCODED: 60 Sekunden

from ble_watchdog_manager import BleDumpWatchdog

watchdog = BleDumpWatchdog(
    timeout=config.get_stale_timeout(),
    interval=1.0,
    callback=lambda x: x
)

watchdog_result = watchdog.check_status()

def update_bridge_state(alive, status, last_seen):
    global BRIDGE_ALIVE, BRIDGE_STATUS, BRIDGE_LAST_SEEN
    BRIDGE_ALIVE = alive
    BRIDGE_STATUS = status
    BRIDGE_LAST_SEEN = last_seen

# ------------------------------------------------------------
# PROFILE LOADER
# ------------------------------------------------------------
def load_profile(name):
    if not name:
        return None

    fname = f"{name}.json"

    candidates = [
        os.path.join(PROFILES, "adv", fname),
        os.path.join(PROFILES, "gatt", fname),
    ]

    for p in candidates:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    prof = json.load(f)
                if isinstance(prof, dict) and prof.get("fields"):
                    return prof
                print("[Decoder] Invalid profile:", p)
                return None
            except Exception:
                print("[Decoder] JSON error:", p)
                return None

    # 🔥 HARTER FEHLER – bewusst
    print("[Decoder] Missing profile (no fallback):", fname)
    return None


# ------------------------------------------------------------
# HELPER
# ------------------------------------------------------------
def _be16(b, pos):
    if pos + 1 >= len(b): return None
    v = (b[pos] << 8) | b[pos+1]
    if v in (0xFFFF, 0x0FFF): return None
    if v & 0x8000: v -= 0x10000
    return v

def _be16u(b, pos):
    if pos + 1 >= len(b): return None
    v = (b[pos] << 8) | b[pos+1]
    if v in (0xFFFF, 0x0FFF): return None
    return v
def _u8(b, pos):
    if pos >= len(b):
        return None
    v = b[pos] & 0xFF
    if v == 0xFF:
        return None
    return v

def _le16(b, pos):
    if pos + 1 >= len(b): 
        return None
    v = b[pos] | (b[pos+1] << 8)
    if v in (0xFFFF, 0x0FFF): 
        return None
    if v & 0x8000: 
        v -= 0x10000
    return v

def _le16u(b, pos):
    if pos + 1 >= len(b): 
        return None
    v = b[pos] | (b[pos+1] << 8)
    if v in (0xFFFF, 0x0FFF): 
        return None
    return v
def _dev_enabled():
    try:
        return config.is_developer_mode()
    except Exception:
        return False


# ------------------------------------------------------------
# DECODIERUNG (roh → Werte)
# ------------------------------------------------------------
def decode_with_profile(raw_hex, prof):
    if not raw_hex or set(raw_hex) == {"0"}:
        return None

    fields = prof.get("fields")
    if not isinstance(fields, dict):
        return None

    try:
        b = bytes.fromhex(raw_hex)
    except Exception:
        return None

    # Company-ID Check & MSD Handling (Lasse ich drin, falls du es brauchst)
    company_id = int(prof.get("company_id", 25))
    cid = (b[1] << 8) | b[0] if len(b) >= 2 else -1

    if cid != company_id:
        msd = bytearray(2 + len(b))
        msd[0] = company_id & 0xFF
        msd[1] = (company_id >> 8) & 0xFF
        msd[2:] = b
        b = bytes(msd)

    # Startoffset bestimmen
    base_offset = int(prof.get("base_offset", 0))
    if base_offset > 0:
        pos = base_offset
    else:
        pos = 2 + int(prof.get("mac_len", 6)) + int(prof.get("skip_after_mac", 2))

    endian = (prof.get("endian") or "le").lower()
    r16  = _be16  if endian == "be" else _le16
    r16u = _be16u if endian == "be" else _le16u

    try:
        # Rohwerte lesen
        ti_raw = r16(b, pos + int(fields["T_i"]))
        hi_raw = r16u(b, pos + int(fields["H_i"]))
        te_raw = r16(b, pos + int(fields["T_e"])) if "T_e" in fields else None
        he_raw = r16u(b, pos + int(fields["H_e"])) if "H_e" in fields else None
        tl_raw = r16(b, pos + int(fields["T_l"])) if "T_l" in fields else None
        vb_raw = r16u(b, pos + int(fields["V_b"])) if "V_b" in fields else None
        fr_raw = r16u(b, pos + int(fields["F_r"])) if "F_r" in fields else None

        sT = float(prof.get("scale_temperature", 100.0))
        sH = float(prof.get("scale_humidity", 100.0))
        sB = float(prof.get("scale_battery", 100.0))

        # -256.0 Check (Berücksichtigt Skalierung vom ESP32)
        # Wenn der Rohwert -25600 ist (entspricht -256.0 nach Scale 100)
        MISSING_VAL = -256.0 * sT 

        te_final = te_raw / sT if (te_raw is not None and te_raw > MISSING_VAL) else None
        he_final = he_raw / sH if (he_raw is not None and he_raw > MISSING_VAL) else None
        tl_final = tl_raw / sT if (tl_raw is not None and tl_raw > MISSING_VAL) else None
        
        # Internal NTC ebenfalls gegen den neuen Standard prüfen
        ti_final = ti_raw / sT if (ti_raw is not None and ti_raw > MISSING_VAL) else None
        hi_final = hi_raw / sH if (hi_raw is not None and hi_raw > MISSING_VAL) else None

        vb_final = vb_raw / sB if vb_raw is not None else None

    except Exception:
        return None

    return {
        "raw": raw_hex,
        "T_i": ti_final, "H_i": hi_final,
        "T_e": te_final, "H_e": he_final,
        "T_l": tl_final, "V_b": vb_final,
        "F_r": fr_raw # <--- RPM zurückgeben
    }
# -----------------------------------------------
# MULTI-CHANNEL DECODER (ADV + GATT)
# -----------------------------------------------

def decode_channel(entry, raw_key, profile_name,
                   last_signal_dict, last_ts_dict,
                   timeout, is_gatt=False):

    now = time.time()
    mac = entry.get("address")

    # Bewegungssignal
    if is_gatt:
        signal = entry.get("packet_counter")
    else:
        signal = entry.get(raw_key)

    if mac is None:
        return offline_channel_frame(entry.get(raw_key))
    
    # signal fehlt → NICHT offline!
    if signal is None:
        # letzten Zustand behalten
        last_ts = last_ts_dict.get(mac)
        if last_ts and (time.time() - last_ts) < float(timeout):
            # KEEP ALIVE (kein neues Signal, aber noch gültig)
            pass
        else:
            return offline_channel_frame(entry.get(raw_key))

    last_signal = last_signal_dict.get(mac)
    last_ts = last_ts_dict.get(mac)

    # Erstkontakt -> merken, aber NICHT sofort offline
    if last_signal is None:
        last_signal_dict[mac] = signal
        last_ts_dict[mac] = now
    else:
        # Bewegung?
        if signal != last_signal:
            last_signal_dict[mac] = signal
            last_ts_dict[mac] = now
        else:
            # keine Bewegung -> nur nach timeout offline
            if last_ts is None:
                last_ts_dict[mac] = now
            elif (now - last_ts) >= float(timeout):
                return offline_channel_frame(entry.get(raw_key))

    # --- Decode stumpf ---
    raw_hex = entry.get(raw_key)
    if not raw_hex:
        return offline_channel_frame(None)

    prof = load_profile(profile_name)
    if not prof:
        return offline_channel_frame(raw_hex)

    decoded = decode_with_profile(raw_hex, prof)
    if not decoded:
        return offline_channel_frame(raw_hex)

    # Offsets anwenden
    T_i, H_i, T_e, H_e = calculator.apply_offsets(
        decoded["T_i"], decoded["H_i"], decoded["T_e"], decoded["H_e"]
    )

    unit = f"°{config.get_temperature_unit().upper()}"
     # 🔹 Koordinaten VOR dem Return berechnen
    xi, yi = calculator.vpd_coord_internal(T_i, H_i)
    xe, ye = calculator.vpd_coord_external(T_e, H_e)
    dpi = calculator.dew_point_internal(T_i, H_i)
    dpe = calculator.dew_point_external(T_e, H_e)
    
    T_l = decoded.get("T_l")
    V_b = decoded.get("V_b")
    
       
# VPD Leaf Berechnung (Sture Formel gegen Internal Humidity)
    # --- NEUE VPD LEAF LOGIK (basiert auf Externen Werten) ---
    vpd_l_val = None
    # Wir brauchen Blatttemp (T_l), sowie externe Lufttemp (T_e) und Luftfeuchte (H_e)
    if T_l is not None and T_e is not None and H_e is not None:
        # 1. SVP Blatt (Sättigungsdampfdruck bei Blatttemperatur)
        svp_l = 0.61078 * (10**((7.5 * T_l) / (237.3 + T_l)))
        
        # 2. AVP Luft (Aktueller Dampfdruck der Umgebungsluft via SHT31)
        # Zuerst Sättigungsdampfdruck der Umgebungsluft berechnen
        svp_e = 0.61078 * (10**((7.5 * T_e) / (237.3 + T_e)))
        # Dann mit der echten Luftfeuchtigkeit (H_e) den tatsächlichen Druck ermitteln
        avp_e = svp_e * (H_e / 100.0)
        
        # 3. Differenz bilden
        vpd_l_val = round(svp_l - avp_e, 3)

    # --- Sauber zurückgeben ---
    return {
        "alive": True,
        "status": "active",
        "packet_counter": entry.get("packet_counter"),
        "raw": decoded["raw"],

        "internal": {
            "temperature": {"value": calculator.to_unit(T_i), "unit": unit},
            "humidity": {"value": H_i, "unit": "%"},
        },
        
        "external": {
            "present": decoded["T_e"] is not None,
            "temperature": {"value": calculator.to_unit(T_e), "unit": unit},
            "humidity": {"value": H_e, "unit": "%"},
        },

        # 🔹 HIER IST DEIN EXTERNAL 2 ZWEIG (Blatt-Daten)
        "external2": {
            "present": T_l is not None,
            "leaf_temp": {"value": calculator.to_unit(T_l), "unit": unit},
            "vpd_leaf": {"value": vpd_l_val, "unit": "kPa"}
        },

        "vpd_internal": {"value": calculator.vpd_internal(T_i, H_i), "unit": "kPa"},
        "vpd_external": {"value": calculator.vpd_external(T_e, H_e), "unit": "kPa"},
        
         
        "battery_voltage": V_b,

        "dew_point_internal": {"value": calculator.to_unit(dpi), "unit": unit},
        "dew_point_external": {"value": calculator.to_unit(dpe), "unit": unit},

        "coord": {
            "internal": {"x": xi, "y": yi},
            "external": {"x": xe, "y": ye},
        }
    }

def offline_channel_frame(raw_hex=None):
    unit = f"°{config.get_temperature_unit().upper()}"
    return {
        "alive": False,
        "status": "offline",
        "packet_counter": None,
        "raw": raw_hex,
        "internal": {
            "temperature": {"value": None, "unit": unit},
            "humidity": {"value": None, "unit": "%"},
        },
        "external": {
            "present": False,
            "temperature": {"value": None, "unit": unit},
            "humidity": {"value": None, "unit": "%"},
        },
        "external2": {
            "present": False,
            "leaf_temp": {"value": None, "unit": unit},
            "vpd_leaf": {"value": None, "unit": "kPa"}
        },
        "vpd_internal": {"value": None, "unit": "kPa"},
        "vpd_external": {"value": None, "unit": "kPa"},
        "battery_voltage": None,
        "dew_point_internal": {"value": None, "unit": unit},
        "dew_point_external": {"value": None, "unit": unit},
        "coord": {
            "internal": {"x": None, "y": None},
            "external": {"x": None, "y": None},
        }
    }

def offline_frame(mac, prof, now):
    # Wir holen uns die IP aus der Config für den Frame
    import config
    ip = config.get_device_ip(mac)

    off_frame = offline_channel_frame()
    # Wir setzen die IP in den Webserver-Slot, damit die UI weiß, wo sie suchen könnte
    web_frame = off_frame.copy()
    web_frame["ip"] = ip 

    return {
        "timestamp": now,
        "device_id": mac,
        "name": config.get_device_name(mac) or None,

        # Die drei Säulen deiner Daten
        "adv": off_frame,
        "gatt": off_frame,
        "webserver": web_frame, # <--- NEU: Die dritte Quelle

        "bridge_alive": BRIDGE_ALIVE,
        "bridge_status": BRIDGE_STATUS,
        "bridge_last_seen": BRIDGE_LAST_SEEN,

        "alive": False,
        "status": "offline",

        "health": {
            "uptime": {"value": None, "unit": "s"},
            "battery": {"value": None, "unit": "V", "voltage": None},
            "signal": {"rssi": None, "quality": None},
        },
    }

def offline_all(cfg):
    now = time.time()
    frames = []

    for mac, d in cfg.get("devices", {}).items():
        prof = load_profile(d.get("decoder_profile", "unknown")) or {}
        frames.append(offline_frame(mac, prof, now))

    _write(frames)
# ------------------------------------------------------------
# DECODER-STEP
# ------------------------------------------------------------





# Ganz oben in decoder.py (bei den Variablen)
_LIVE_WEB_DATA = {} # Das hier ist unser neuer Hochgeschwindigkeits-Speicher

def inject_web_data(mac, payload):
    """Wird direkt vom WebClient aufgerufen - Umgeht das Dateisystem!"""
    global _LIVE_WEB_DATA
    _LIVE_WEB_DATA[mac] = payload

def step_decode():
    global UPTIME_START, _LAST_ADV_RAW, _LAST_GATT_RAW, _LAST_WEB, _LIVE_WEB_DATA
    cfg = config._init()
    devs = cfg.get("devices", {})
    now = time.time()
    if UPTIME_START is None: UPTIME_START = now

    # 1. WATCHDOG LADEN
    w_res = watchdog.check_status()
    w_devs = w_res.get("devices", {})

    # BLE Daten laden
    ble_list = []
    if os.path.exists(RAW_FILE):
        try:
            with open(RAW_FILE, "r") as f: 
                ble_list = json.load(f)
        except: pass
    
    # 2. WEB DATEN LADEN (RAM + DISK BACKUP)
    # Wir nehmen Daten aus dem RAM, aber falls leer, lesen wir die Datei
    web_data = _LIVE_WEB_DATA.copy() 
    if not web_data:
        web_dump_path = os.path.join(DATA, "web_dump.json")
        if os.path.exists(web_dump_path):
            try:
                with open(web_dump_path, "r") as f:
                    web_data = json.load(f)
            except: pass

    by_mac = {e.get("address"): e for e in ble_list if isinstance(e, dict) and e.get("address")}
    timeout = float(config.get_stale_timeout())
    frames = []

    for mac, dev_cfg in devs.items():
        entry = by_mac.get(mac)
        w_status = w_devs.get(mac, {})
        unit = f"°{config.get_temperature_unit().upper()}"

        # --- KANAL 1: ADV ---
        adv_w = w_status.get("adv", {"alive": False})
        adv_dec = offline_channel_frame(entry.get("adv_raw") if entry else None)
        if adv_w["alive"]:
            res = decode_channel(entry, "adv_raw", dev_cfg.get("adv_decoder"), _LAST_ADV_RAW, _LAST_ADV_TS, timeout) if entry else None
            if res and res["alive"]:
                adv_dec = res
                _LAST_ADV_RAW[mac] = entry.get("adv_raw")
            elif mac in _LAST_ADV_RAW:
                adv_dec = decode_channel({"address": mac, "adv_raw": _LAST_ADV_RAW[mac]}, "adv_raw", dev_cfg.get("adv_decoder"), _LAST_ADV_RAW, _LAST_ADV_TS, timeout)

# --- KANAL 2: GATT (REPARIERT & KUGELSICHER) ---
        gatt_w = w_status.get("gatt", {"alive": False})
        raw_from_entry = entry.get("gatt_raw") if entry else None
        gatt_dec = offline_channel_frame(raw_from_entry)

        if gatt_w["alive"] and entry:
            res = decode_channel(entry, "gatt_raw", dev_cfg.get("gatt_decoder"), _LAST_GATT_RAW, _LAST_GATT_TS, timeout, is_gatt=True)
            if res and res["alive"]:
                gatt_dec = res
                _LAST_GATT_RAW[mac] = raw_from_entry # Hier sicher TT

        # Wenn der Kanal gerade tot ist, zieh den JOKER aus dem RAM
        if not gatt_dec["alive"] and mac in _LAST_GATT_RAW:
            gold_data = _LAST_GATT_RAW[mac] # Hier sicher TT
            res_cache = decode_channel({"address": mac, "gatt_raw": gold_data}, "gatt_raw", dev_cfg.get("gatt_decoder"), _LAST_GATT_RAW, _LAST_GATT_TS, timeout, is_gatt=True)
            if res_cache and res_cache["alive"]:
                gatt_dec = res_cache
        # --- KANAL 3: WEBSERVER (WATCHDOG-FREI & STABIL) ---
        # Wir ignorieren web_w = w_status.get("web") komplett!
        
        # --- KANAL 3: WEBSERVER (WATCHDOG-FREI & STABIL) ---
        web_raw = web_data.get(mac)
        if web_raw: 
            _LAST_WEB[mac] = web_raw 

        # 1. WICHTIG: IMMER sauberen Offline-Frame als Basis (leert alte Daten!)
        web_dec = offline_channel_frame() 
        current_web = _LAST_WEB.get(mac)
        
        web_alive = False
        if current_web:
            web_ts = current_web.get("timestamp")
            # Zeit-Check gegen Config-Timeout
            if web_ts and (now - web_ts) < float(config.get_stale_timeout()):
                web_alive = True

        if web_alive:
            # --- SENSOR-STATUS CHECK (DIE RETTUNG) ---
            ERR_VAL = -256.0
            raw_t_e = current_web.get("temp_ext")
            raw_h_e = current_web.get("humid_ext")

            # Erkennung ob Sensor physisch vorhanden (Größer als -256)
            sensor_exists = (raw_t_e is not None and raw_t_e > ERR_VAL)
            # Blatt-Sensor vorhanden? (Eigener Check!)
            raw_t_l = current_web.get("leaf_temp")
            leaf_exists = (raw_t_l is not None and raw_t_l > ERR_VAL)
            
            # Bereinigte Werte für den Calculator (None erzwingt "---" in der UI)
            t_e_final = raw_t_e if sensor_exists else None
            h_e_final = raw_h_e if sensor_exists else None

            # JETZT die bereinigten Werte nutzen!
            T_i, H_i, T_e, H_e = calculator.apply_offsets(
                current_web.get("temp_in"), current_web.get("humid_in"),
                t_e_final, h_e_final
            )
            
            # Hilfswerte für Berechnungen
            vpdi = calculator.vpd_internal(T_i, H_i)
            vpde = calculator.vpd_external(T_e, H_e)
            dpi = calculator.dew_point_internal(T_i, H_i)
            dpe = calculator.dew_point_external(T_e, H_e)
            xi, yi = calculator.vpd_coord_internal(T_i, H_i)
            xe, ye = calculator.vpd_coord_external(T_e, H_e)

            web_dec.update({
                "alive": True,
                "status": "active",
            
                "internal": {
                    "temperature": {"value": calculator.to_unit(T_i), "unit": unit}, 
                    "humidity": {"value": H_i, "unit": "%"},
                },
            
                "external": {
                    "present": sensor_exists,
                    "temperature": {"value": calculator.to_unit(T_e), "unit": unit}, 
                    "humidity": {"value": H_e, "unit": "%"},
                },
            
                # 🔥 IDENTISCH ZU ADV/GATT (TOP LEVEL!)
                "vpd_internal": {"value": vpdi, "unit": "kPa"},
                "vpd_external": {"value": vpde, "unit": "kPa"},
            
                "dew_point_internal": {"value": calculator.to_unit(dpi), "unit": unit},
                "dew_point_external": {"value": calculator.to_unit(dpe), "unit": unit},
            
                "coord": {
                    "internal": {"x": xi, "y": yi}, 
                    "external": {"x": xe if sensor_exists else None, "y": ye if sensor_exists else None}
                },
            
                "battery_voltage": current_web.get("vbat"),
                "timestamp": web_ts,
            
                "circulation_fan": {"circulation_fan_rpm": current_web.get("circulation_fan_rpm", 0), "unit": "RPM"},
                "exhaust_fan": {"exhaust_fan_rpm": current_web.get("exhaust_fan_rpm", 0), "unit": "RPM"},
            
                "light_pct": current_web.get("light_pct", 0),
                "light_mode": current_web.get("light_mode", "off"),
                "rev": current_web.get("rev"),
                "health": current_web.get("health")
            })
            # --- JETZT: UNABHÄNGIGE LEAF-LOGIK ---
            if leaf_exists:
                # Blatt-Temp ist da. VPD Leaf braucht aber T_e und H_e als Referenz!
                # Wenn kein SHT31 da ist, nehmen wir Internal als Notbehelf für die Luftwerte
                ref_t = T_e if sensor_exists else T_i
                ref_h = H_e if sensor_exists else H_i
                
                # SVP Blatt
                svp_l = 0.61078 * (10**((7.5 * raw_t_l) / (237.3 + raw_t_l)))
                # AVP Luft (Referenz: External oder Internal)
                svp_ref = 0.61078 * (10**((7.5 * ref_t) / (237.3 + ref_t)))
                avp_ref = svp_ref * (ref_h / 100.0)
                
                web_dec["external2"] = {
                    "present": True,
                    "leaf_temp": {"value": calculator.to_unit(raw_t_l), "unit": unit},
                    "vpd_leaf": {"value": round(svp_l - avp_ref, 3), "unit": "kPa"}
                }
        # --- FINAL MERGE ---
        web_rssi = web_dec.get("health", {}).get("signal", {}).get("rssi") if isinstance(web_dec.get("health"), dict) else None
        ble_rssi = entry.get("rssi") if (adv_w["alive"] or gatt_w["alive"]) and entry else None
        final_rssi = web_rssi if web_rssi is not None else ble_rssi

        is_alive = any([adv_dec["alive"], gatt_dec["alive"], web_dec["alive"]])
        if not is_alive: final_rssi = None

        frames.append({
            "timestamp": now,
            "device_id": mac,
            "name": dev_cfg.get("name", mac),
            "adv": adv_dec,
            "gatt": gatt_dec,
            "webserver": web_dec,
            "alive": is_alive,
            "status": "active" if is_alive else "offline",
            "health": {
                "uptime": {"value": now - UPTIME_START, "unit": "s"},
                "battery": {"value": None, "unit": "V", "voltage": web_dec.get("battery_voltage") or adv_dec.get("battery_voltage")},
                "signal": {"rssi": final_rssi, "quality": None}
            }
        })
    _write(frames)
# ------------------------------------------------------------

def _write(frames):
    global _LAST_LOG_TS, _LAST_WRITE_TS, _LAST_HASH
    global _DECODED_RAM, _DECODED_TS

    if not frames:
        return

    now = time.time()

    # 🔥 1. IMMER RAM UPDATEN (SOFORT)
    _DECODED_RAM = frames
    _DECODED_TS = now

    # 🔥 HASH für Disk-Write
    current_hash = hash(str(frames))

    # 🔥 2. DISK NUR SELTEN
    DISK_INTERVAL = 60.0   # <<<< DAS IST DEIN NEUER MASTER

    if (now - _LAST_WRITE_TS) >= DISK_INTERVAL:
        _write_atomic(DEC_FILE, frames)
        _LAST_WRITE_TS = now
        _LAST_HASH = current_hash

    # CSV bleibt
    if _dev_enabled() and (now - _LAST_LOG_TS) >= _LOG_INTERVAL:
        _write_csv(frames)
        _LAST_LOG_TS = now

def _write_atomic(filename, data):
    """Garantiert, dass die UI niemals eine halbfertige Datei liest"""
    tmp = filename + ".tmp"
    try:
        # Erst den JSON-String im Arbeitsspeicher (RAM) erstellen
        # Das dauert am längsten, blockiert aber die Datei noch nicht
        json_string = json.dumps(
            data,
            indent=2,
            ensure_ascii=False
        )        
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(json_string)
            f.flush()
            os.fsync(f.fileno())
            
        # Jetzt die Datei blitzschnell ersetzen
        os.replace(tmp, filename)
    except Exception as e:
        print(f"[Decoder] Atomic Write Error: {e}")

def get_decoded_ram():
    return _DECODED_RAM

def get_decoded_timestamp():
    return _DECODED_TS

def _write_csv(frames):
    file_exists = os.path.exists(CSV_FILE)

    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Header nur einmal schreiben
        if not file_exists:
            writer.writerow([
                "timestamp",
                "device_id",
                "name",
                "channel",
                "alive",
                "status",
                "packet_counter",
                "raw",
                "T_i",
                "H_i",
                "T_e",
                "H_e",
                "vpd_i",
                "vpd_e",
                "rssi"
            ])

        for frame in frames:
            for channel in ("adv", "gatt", "webserver"):
                ch = frame.get(channel, {})

                writer.writerow([
                    frame.get("timestamp"),
                    frame.get("device_id"),
                    frame.get("name"),
                    channel,
                    ch.get("alive"),
                    ch.get("status"),
                    ch.get("packet_counter"),
                    ch.get("raw"),

                    ch.get("internal", {}).get("temperature", {}).get("value"),
                    ch.get("internal", {}).get("humidity", {}).get("value"),

                    ch.get("external", {}).get("temperature", {}).get("value"),
                    ch.get("external", {}).get("humidity", {}).get("value"),

                    ch.get("vpd_internal", {}).get("value"),
                    ch.get("vpd_external", {}).get("value"),

                    frame.get("health", {}).get("signal", {}).get("rssi")
                ])

class DecoderThread(threading.Thread):
    def __init__(self, interval=1.0):
        super().__init__(daemon=True)
        self.running = True
        self.interval = interval

    def run(self):
        while self.running:
            step_decode()
            time.sleep(self.interval)

    def stop(self):
        self.running = False

decoder_thread = None

def start_decoder_thread(interval=1.0):
    global decoder_thread
    if decoder_thread:
        return
    decoder_thread = DecoderThread(interval)
    decoder_thread.start()
    print("[Decoder] Thread started")
def _ensure_csv_cleared():
    try:
        if os.path.exists(CSV_FILE):
            os.remove(CSV_FILE)
    except Exception:
        pass
