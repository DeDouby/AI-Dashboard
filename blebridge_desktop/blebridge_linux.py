#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
blebridge_linux_smooth.py – Smooth RAW BLE Scanner für BlueZ/Linux
© 2026 Dominik Rosenthal
"""

import os
import sys
import time
import json
import asyncio
import threading
from datetime import datetime, timezone

from bleak import BleakScanner

# Projekt-Root = eine Ebene über blebridge_desktop/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUT_FILE = os.path.join(DATA_DIR, "ble_dump.json")

WRITE_INTERVAL = 3.0
SCAN_IDLE_SLEEP = 0.2

def ts_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+0000"

class Store:
    def __init__(self):
        self.lock = threading.Lock()
        self.last = {}

    def update(self, ident, name, rssi, msd):
        adv_hex = msd.hex().upper() if msd else ""
        rssi_val = int(rssi) if rssi is not None else 0
        with self.lock:
            dev = self.last.get(ident, {
                "timestamp": ts_iso(),
                "name": name,
                "address": ident,
                "rssi": rssi_val,
                "adv_raw": None,
                "gatt_raw": None,
                "log_raw": None,
                "note": "raw"
            })
            dev["timestamp"] = ts_iso()
            dev["name"] = name
            dev["rssi"] = rssi_val
            dev["adv_raw"] = adv_hex
            dev["log_raw"] = adv_hex
            self.last[ident] = dev

    def snapshot(self):
        with self.lock:
            return list(self.last.values())

class WriterThread(threading.Thread):
    def __init__(self, store):
        super().__init__(daemon=True)
        self.store = store
        self.run_flag = True
        os.makedirs(DATA_DIR, exist_ok=True)

    def run(self):
        while self.run_flag:
            try:
                tmp = OUT_FILE + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(self.store.snapshot(), f, ensure_ascii=False, indent=2)
                os.replace(tmp, OUT_FILE)
            except Exception as e:
                print("write err:", e)
            time.sleep(WRITE_INTERVAL)

    def stop(self):
        self.run_flag = False

async def scan_loop(store):
    def detection_callback(device, advertisement_data):
        try:
            name = device.name or "(unknown)"
            rssi = advertisement_data.rssi  # ← jetzt korrekt
            msd = advertisement_data.manufacturer_data
            msd_bytes = b"".join(msd.values()) if msd else None
            ident = device.address
            store.update(ident, name, rssi, msd_bytes)
        except Exception as e:
            print("discover err:", e, file=sys.stderr)

    print("[SmoothBLE] Running…")
    scanner = BleakScanner(detection_callback=detection_callback)

    try:
        while True:
            await scanner.start()
            await asyncio.sleep(SCAN_IDLE_SLEEP)
            await scanner.stop()
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    except Exception as e:
        print("scan err:", e, file=sys.stderr)

def main():
    print("[SmoothBLE] START")
    store = Store()
    writer = WriterThread(store)
    writer.start()

    try:
        asyncio.run(scan_loop(store))
    finally:
        writer.stop()
        print("[SmoothBLE] STOP")

if __name__ == "__main__":
    main()

