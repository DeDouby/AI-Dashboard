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

    if not raw_hex:
        return None

    # 🔒 ABSICHERUNG: Null-Frames ignorieren
    if set(raw_hex) == {"0"}:
        return None


    fields = prof.get("fields")
    if not isinstance(fields, dict):
        return None

    try:
        b = bytes.fromhex(raw_hex)
    except Exception:
        return None

    # Company-ID aus Profil (nur für ADV-Kompatibilität)
    company_id = int(prof.get("company_id", 25))
    cid = (b[1] << 8) | b[0] if len(b) >= 2 else -1

    # Falls CID nicht passt → MSD vorne dransetzen (ADV-Altlast, stört GATT nicht)
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
        ti = r16(b, pos + int(fields["T_i"]))
    
        hi_mode = (prof.get("H_i_type") or "u16").lower()
        if hi_mode == "u8":
            hi = _u8(b, pos + int(fields["H_i"]))
        else:
            hi = r16u(b, pos + int(fields["H_i"]))
    
        te = None
        he = None
    
        if int(fields.get("T_e", 100)) < 100:
            te = r16(b, pos + int(fields["T_e"]))
    
        if int(fields.get("H_e", 100)) < 100:
            he = r16u(b, pos + int(fields["H_e"]))
    
    except Exception:
        return None

    sT = float(prof.get("scale_temperature", 16))
    sH = float(prof.get("scale_humidity", 16))

    return {
        "raw": raw_hex,          # RAW bleibt unverändert sichtbar
        "T_i": ti / sT if ti is not None else None,
        "H_i": hi / sH if hi is not None else None,
        "T_e": te / sT if te is not None else None,
        "H_e": he / sH if he is not None else None,
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

        "vpd_internal": {"value": calculator.vpd_internal(T_i, H_i), "unit": "kPa"},
        "vpd_external": {"value": calculator.vpd_external(T_e, H_e), "unit": "kPa"},

        "dew_point_internal": {
            "value": calculator.dew_point_internal(T_i, H_i),
            "unit": unit
        },
        "dew_point_external": {
            "value": calculator.dew_point_external(T_e, H_e),
            "unit": unit
        },

        "coord": {
            "internal": {"x": xi, "y": yi},
            "external": {"x": xe, "y": ye},
        }
    }


def offline_channel_frame(raw_hex=None):
    return {
        "alive": False,
        "status": "offline",
        "packet_counter": None,
        "raw": raw_hex,
        "internal": {
            "temperature": {"value": None, "unit": f"°{config.get_temperature_unit().upper()}"},
            "humidity": {"value": None, "unit": "%"},
        },
        "external": {
            "present": False,
            "temperature": {"value": None, "unit": f"°{config.get_temperature_unit().upper()}"},
            "humidity": {"value": None, "unit": "%"},
        },
        "vpd_internal": {"value": None, "unit": "kPa"},
        "vpd_external": {"value": None, "unit": "kPa"},

        "dew_point_internal": {
            "value": None,
            "unit": f"°{config.get_temperature_unit().upper()}"
        },
        "dew_point_external": {
            "value": None,
            "unit": f"°{config.get_temperature_unit().upper()}"
        },

        "coord": {
            "internal": {"x": None, "y": None},
            "external": {"x": None, "y": None},
        }
    }


def offline_frame(mac, prof, now):
    return {
        "timestamp": now,
        "device_id": mac,
        "name": None,

        # 🔒 WICHTIG: beide Kanäle IMMER vollständig
        "adv": offline_channel_frame(),
        "gatt": offline_channel_frame(),

        "bridge_alive": BRIDGE_ALIVE,
        "bridge_status": BRIDGE_STATUS,
        "bridge_last_seen": BRIDGE_LAST_SEEN,

        "alive": False,
        "status": "offline",

        "health": {
            "uptime": {"value": None, "unit": "s"},
            "battery": {"value": None, "unit": "%", "voltage": None},
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

        # ------------------------------
        # DEVICE OFFLINE
        # ------------------------------
        if entry is None:
            pname = dev_cfg.get("adv_decoder") or dev_cfg.get("gatt_decoder") or "unknown"
            prof = load_profile(pname) or {}
            frames.append(offline_frame(mac, prof, now))
            continue

        # ------------------------------
        # ADV
        # ------------------------------
        adv_dec = decode_channel(
            entry, "adv_raw",
            dev_cfg.get("adv_decoder", "unknown"),
            _LAST_ADV_RAW, _LAST_ADV_TS,
            timeout,
            is_gatt=False
        )

        # ------------------------------
        # GATT (Counter-Tick relevant)
        # ------------------------------
        gatt_dec = decode_channel(
            entry, "gat_raw",
            dev_cfg.get("gatt_decoder", "unknown"),
            _LAST_GATT_RAW, _LAST_GATT_TS,
            timeout,
            is_gatt=True
        )

        # ------------------------------
        # BEIDE TOT → OFFLINE
        # ------------------------------
        if not (adv_dec and adv_dec.get("alive")) and not (gatt_dec and gatt_dec.get("alive")):
            pname = dev_cfg.get("adv_decoder") or dev_cfg.get("gatt_decoder") or "unknown"
            prof = load_profile(pname) or {}
            frames.append(offline_frame(mac, prof, now))
            continue

        # ------------------------------
        # DEVICE STATUS
        # ------------------------------
        adv_alive  = bool(adv_dec and adv_dec.get("alive"))
        gatt_alive = bool(gatt_dec and gatt_dec.get("alive"))
        alive = adv_alive or gatt_alive

        if not adv_alive:
            adv_dec = offline_channel_frame(entry.get("adv_raw"))
        if not gatt_alive:
            gatt_dec = offline_channel_frame(entry.get("gat_raw"))

        # ------------------------------
        # FINAL FRAME
        # ------------------------------
        rssi_value = entry.get("rssi") if alive else None

        frames.append({
            "timestamp": entry.get("timestamp"),
            "device_id": mac,
            "name": entry.get("name"),

            "adv": adv_dec,
            "gatt": gatt_dec,

            "bridge_alive": BRIDGE_ALIVE,
            "bridge_status": BRIDGE_STATUS,
            "bridge_last_seen": BRIDGE_LAST_SEEN,

            "alive": alive,
            "status": "active" if alive else "offline",

            "health": {
                "uptime": {"value": now - UPTIME_START, "unit": "s"},
                "battery": {"value": None, "unit": "%", "voltage": None},
                "signal": {
                    "rssi": rssi_value,
                    "quality": None
                },
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
