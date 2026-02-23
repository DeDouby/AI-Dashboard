#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
blebridge_desktop_smooth.py – Smooth RAW BLE Scanner
© 2025 Dominik Rosenthal
"""

import json, time, threading, os, sys
from datetime import datetime, timezone

from kivy.app import App
from kivy.clock import Clock

from Foundation import NSObject, NSRunLoop, NSDate
import CoreBluetooth as CB

# Projekt-Root = eine Ebene über blebridge_desktop/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUT_FILE = os.path.join(DATA_DIR, "ble_dump.json")

WRITE_INTERVAL = 3.0        # CPU halbiert → weniger File IO
SCAN_IDLE_SLEEP = 0.20      # kleine Pause → CPU -30%

def ts_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+0000"


class Store:
    def __init__(self):
        self.lock = threading.Lock()
        self.last = {}

    def update(self, ident, name, rssi, msd):
        adv_hex = msd.hex().upper() if msd else ""

        with self.lock:
            dev = self.last.get(ident, {
                "timestamp": ts_iso(),
                "name": name,
                "address": ident,
                "rssi": int(rssi),
                "adv_raw": None,
                "gat_raw": None,
                "log_raw": None,
                "note": "raw"   # exakt wie Session 44
            })

            dev["timestamp"] = ts_iso()
            dev["name"] = name
            dev["rssi"] = int(rssi)
            dev["adv_raw"] = adv_hex
            dev["log_raw"] = adv_hex

            self.last[ident] = dev

    def snapshot(self):
        with self.lock:
            # 🔥 FIX: Ausgabe als LISTE – kompatibel zu Session 44 & Android
            return list(self.last.values())

class CentralDelegate(NSObject):  # 🔥 Wichtig: Originalklasse unverändert!
    def initWithStore_(self, store):
        self = self.init()
        if self is None:
            return None
        self.store = store
        return self

    def centralManagerDidUpdateState_(self, manager):
        if manager.state() == CB.CBManagerStatePoweredOn:
            manager.scanForPeripheralsWithServices_options_(
                None, {"kCBScanOptionAllowDuplicatesKey": True}
            )
        else:
            print("Bluetooth state:", manager.state())

    def centralManager_didDiscoverPeripheral_advertisementData_RSSI_(
        self, m, p, adv, rssi
    ):
        try:
            name = adv.get(CB.CBAdvertisementDataLocalNameKey) or p.name() or "(unknown)"
            msd = adv.get(CB.CBAdvertisementDataManufacturerDataKey)
            ident = str(p.identifier())
            self.store.update(ident, name, rssi, bytes(msd) if msd else None)
        except Exception as e:
            print("discover err:", e, file=sys.stderr)


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


def scan_loop(store):
    delegate = CentralDelegate.alloc().initWithStore_(store)
    central = CB.CBCentralManager.alloc().initWithDelegate_queue_options_(
        delegate, None, None
    )

    rl = NSRunLoop.currentRunLoop()
    print("[SmoothBLE] Running…")

    while True:
        try:
            rl.runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.1))
            time.sleep(SCAN_IDLE_SLEEP)  # 🔥 CPU smoother – ohne Logik ändern!
        except KeyboardInterrupt:
            break


def main():
    print("[SmoothBLE] START")

    store = Store()
    writer = WriterThread(store)
    writer.start()

    try:
        scan_loop(store)
    finally:
        writer.stop()
        print("[SmoothBLE] STOP")


if __name__ == "__main__":
    main()
