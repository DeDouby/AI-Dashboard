#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

_LAST_RAW = {}
_LAST_TS = {}
# Stale-Handling pro Kanal
_LAST_ADV_RAW = {}
_LAST_ADV_TS = {}

_LAST_GATT_RAW = {}
_LAST_GATT_TS = {}

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
                prof = json.load(open(p, "r", encoding="utf-8"))
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
_profile_cache = {}  # Cache für geladene Profile

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

    if mac is None or signal is None:
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
        
        "fan": {
            "speed_rpm": decoded.get("F_r", 0),
            "unit": "RPM"
        },        
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
def step_decode():
    global UPTIME_START

    cfg = config._init()
    devs = cfg.get("devices", {})

    if not devs or not os.path.exists(RAW_FILE):

        return offline_all(cfg)

    try:
        raw_list = json.load(open(RAW_FILE, "r"))
    except:
        return offline_all(cfg)

    if not isinstance(raw_list, list):
        return offline_all(cfg)
    
    # NEU: Web-Daten laden
    web_data = {}
    web_dump_path = os.path.join(DATA, "web_dump.json")
    if os.path.exists(web_dump_path):
        try:
            with open(web_dump_path, "r") as f:
                web_data = json.load(f)
        except:
            pass
    now = time.time()
    if UPTIME_START is None:
        UPTIME_START = now

    timeout = float(config.get_stale_timeout())

    by_mac = {
        e.get("address"): e
        for e in raw_list
        if isinstance(e, dict) and e.get("address")
    }

    frames = []

    for mac, dev_cfg in devs.items():
        entry = by_mac.get(mac)
        
        # --- 2. KANÄLE DECODIEREN ---
        # ADV & GATT (wie bisher)
        adv_dec = decode_channel(entry, "adv_raw", dev_cfg.get("adv_decoder", "unknown"), 
                                 _LAST_ADV_RAW, _LAST_ADV_TS, timeout) if entry else offline_channel_frame()
        
        gatt_dec = decode_channel(entry, "gat_raw", dev_cfg.get("gatt_decoder", "unknown"), 
                                  _LAST_GATT_RAW, _LAST_GATT_TS, timeout, is_gatt=True) if entry else offline_channel_frame()

        # --- 3. NEU: WEBSERVER KANAL BEFÜLLEN ---
# --- 3. NEU: WEBSERVER KANAL BEFÜLLEN ---
        web_raw = web_data.get(mac)
        web_dec = offline_channel_frame() # Hier wird die Basis-Struktur geholt
        
        # --- Ausschnitt aus deiner decoder.py (step_decode) ---
        if web_raw:
            web_dec["alive"] = True
            web_dec["status"] = "active"
            
            # 1. Internal
            web_dec["internal"]["temperature"]["value"] = calculator.to_unit(web_raw.get("temp_in"))
            web_dec["internal"]["humidity"]["value"] = web_raw.get("humid_in", 40.0)
            web_dec["vpd_internal"]["value"] = web_raw.get("vpd_in")
        
            # 2. External (Luft)
            t_e = web_raw.get("temp_ext")
            h_e = web_raw.get("humid_ext")
            if t_e is not None:
                web_dec["external"]["present"] = True
                web_dec["external"]["temperature"]["value"] = calculator.to_unit(t_e)
                web_dec["external"]["humidity"]["value"] = h_e
                web_dec["vpd_external"]["value"] = web_raw.get("vpd_ext")
        
            # 3. External2 (Blatt-Daten) -> PASST JETZT ZU BLE
            t_l = web_raw.get("temp_leaf", t_e) # Fallback auf temp_ext wenn nicht separat
            v_l = web_raw.get("vpd_leaf")
            if t_l is not None:
                web_dec["external2"]["present"] = True
                web_dec["external2"]["leaf_temp"]["value"] = calculator.to_unit(t_l)
                web_dec["external2"]["vpd_leaf"]["value"] = v_l
        
         

            # --- FIX FÜR DEN KEYERROR ---
            # Wir stellen sicher, dass "fan" existiert, bevor wir "speed_rpm" setzen
            if "fan" not in web_dec:
                web_dec["fan"] = {"speed_rpm": 0, "unit": "RPM"}
            
            web_dec["fan"]["speed_rpm"] = web_raw.get("rpm", 0)
            web_dec["battery_voltage"] = web_raw.get("vbat")
            
        # --- 4. FINALER FRAME ---
        # Alive ist das Gerät, wenn IRGENDEIN Kanal Daten liefert
        alive = adv_dec.get("alive") or gatt_dec.get("alive") or web_dec.get("alive")

        frames.append({
            "timestamp": now,
            "device_id": mac,
            "name": dev_cfg.get("name", mac),
            "adv": adv_dec,
            "gatt": gatt_dec,
            "webserver": web_dec, # <--- DA IST ER!
            "alive": alive,
            "status": "active" if alive else "offline",
            "health": {
                "uptime": {"value": now - UPTIME_START, "unit": "s"},
                "battery": {"value": None, "unit": "V", "voltage": web_dec["battery_voltage"] or adv_dec.get("battery_voltage")},
                "signal": {"rssi": entry.get("rssi") if entry else None, "quality": None},
            }
        })

    _write(frames)


# ------------------------------------------------------------
def _write(frames):
    tmp = DEC_FILE + ".tmp"
    json.dump(frames, open(tmp, "w"), indent=2)
    os.replace(tmp, DEC_FILE)

    if _dev_enabled():
        _write_csv(frames)
        print("[Decoder] decoded.json + log.csv written")
    else:
        _ensure_csv_cleared()

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
            for channel in ("adv", "gatt"):
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
