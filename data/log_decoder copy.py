# data/log_decoder.py
# Standalone BLE Log Decoder (Desktop)
# © 2026 Dominik Rosenthal

import json
import os
from collections import defaultdict
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INPUT_FILE = os.path.join(BASE_DIR, "ble_log_dump.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "log_decoded.json")


def load_log(path):
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    entries = []
    current = {}

    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()

            if not line:
                continue

            # Start eines Objekts
            if line.startswith("{"):
                current = {}
                continue

            # Ende eines Objekts
            if line.startswith("}"):
                if current:
                    entries.append(current)
                current = {}
                continue

            # key-value Zeilen
            if ":" in line:
                try:
                    key, value = line.split(":", 1)
                    key = key.strip().strip('"')
                    value = value.strip().rstrip(",")

                    if value == "null":
                        value = None
                    elif value.startswith('"') and value.endswith('"'):
                        value = value.strip('"')
                    else:
                        try:
                            value = int(value)
                        except ValueError:
                            pass

                    current[key] = value
                except Exception as e:
                    print(f"⚠️ parse error line {lineno}: {e}")

    return entries



def group_by_device(log_entries):
    devices = defaultdict(list)
    for entry in log_entries:
        addr = entry.get("address", "UNKNOWN")
        devices[addr].append(entry)
    return devices
from collections import defaultdict

def analyze_commands(logs):
    cmd_map = defaultdict(list)
    for entry in logs:
        cmd = entry.get("command")
        raw = entry.get("gat_raw")
        if cmd is not None and raw:
            cmd_map[cmd].append(raw)
    analysis = {}
    for cmd, raws in cmd_map.items():
        unique_raws = set(raws)
        analysis[cmd] = {
            "count": len(raws),
            "unique_count": len(unique_raws),
            "sample_raws": list(unique_raws)[:3]
        }
    return analysis


def decode_entry(entry):
    """
    History-Log Decoder – nur Timestamp und einfache Werte.
    Kein ADV/GATT, keine Flags.
    """
    # Kopiere alles Grundlegende
    decoded = dict(entry)

    # Länge des Rohdatenfeldes (falls vorhanden)
    raw = entry.get("gat_raw")
    decoded["raw_len"] = len(raw) // 2 if raw else 0

    # Timestamp → ISO-Format
    ts = entry.get("timestamp")
    if isinstance(ts, (int, float)):
        # Unix-Timestamp
        try:
            decoded["timestamp_iso"] = datetime.fromtimestamp(ts).isoformat()
        except Exception:
            decoded["timestamp_iso"] = None
    elif isinstance(ts, str):
        # ISO-String oder bereits lesbares Format → übernehmen
        decoded["timestamp_iso"] = ts
    else:
        decoded["timestamp_iso"] = None

    # Defensive Defaults für bekannte Felder
    decoded["temperature_c"] = entry.get("temperature_c", None)
    decoded["humidity_pct"] = entry.get("humidity_pct", None)
    decoded["status"] = entry.get("status", None)

    return decoded





def decode_devices(grouped):
    result = {}

    for addr, entries in grouped.items():
        result[addr] = {
            "count": len(entries),
            "entries": [decode_entry(e) for e in entries]
        }

    return result


def main():
    print("📥 loading:", INPUT_FILE)
    log = load_log(INPUT_FILE)

    print("🔀 grouping by device")
    grouped = group_by_device(log)

    print("🧠 decoding")
    decoded = decode_devices(grouped)

    print("💾 writing:", OUTPUT_FILE)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(decoded, f, indent=2)

    print("✅ done")
    print("   devices:", len(decoded))


if __name__ == "__main__":
    main()
