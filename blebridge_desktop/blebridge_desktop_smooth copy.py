#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
blebridge_desktop_smooth.py – Stabilisierter RAW BLE Scanner für LGS
"""

import json, time, threading, os, sys
from datetime import datetime, timezone
from Foundation import NSObject, NSRunLoop, NSDate
import CoreBluetooth as CB

# Pfade
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUT_FILE = os.path.join(DATA_DIR, "ble_dump.json")

WRITE_INTERVAL = 3.0
SCAN_IDLE_SLEEP = 0.20

def ts_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+0000"

class Store:
    def __init__(self):
        self.lock = threading.Lock()
        self.last = {}

    def update(self, ident, name, rssi, msd):
        adv_hex = msd.hex().upper() if msd else ""
        
        # --- LOGIK: LGS NORMALISIERUNG ---
        # Erkennt deinen Broadcaster am Header 5900 (Company) + A1 (Typ)
        is_lgs = adv_hex.startswith("5900A1")
        
        effective_ident = ident
        effective_name = name

        if is_lgs:
            # Wir mappen alle wechselnden Apple-UUIDs auf diese feste ID
            effective_ident = "FF-FF-A1-00-00-01" 
            effective_name = "LGS_BROADCAST"
            
            with self.lock:
                # Entfernt die ursprüngliche Zufalls-ID, damit die Liste sauber bleibt
                if ident in self.last and ident != effective_ident:
                    del self.last[ident]

        with self.lock:
            # Bestehenden Eintrag (stabil) holen oder neu anlegen
            dev = self.last.get(effective_ident, {
                "timestamp": ts_iso(),
                "name": effective_name,
                "address": effective_ident,
                "rssi": int(rssi),
                "adv_raw": adv_hex,
                "gat_raw": None,
                "log_raw": adv_hex,
                "note": "raw"
            })

            dev["timestamp"] = ts_iso()
            dev["name"] = effective_name
            dev["rssi"] = int(rssi)
            dev["adv_raw"] = adv_hex
            dev["log_raw"] = adv_hex
            
            if is_lgs:
                dev["note"] = "lgs_normalized"

            self.last[effective_ident] = dev

    def snapshot(self):
        with self.lock:
            return list(self.last.values())

class CentralDelegate(NSObject):
    def initWithStore_(self, store):
        self = self.init()
        if self is None: return None
        self.store = store
        return self

    def centralManagerDidUpdateState_(self, manager):
        if manager.state() == CB.CBManagerStatePoweredOn:
            manager.scanForPeripheralsWithServices_options_(
                None, {"kCBScanOptionAllowDuplicatesKey": True}
            )
        else:
            print(f"Bluetooth Status: {manager.state()}")

    def centralManager_didDiscoverPeripheral_advertisementData_RSSI_(self, m, p, adv, rssi):
        try:
            # Name priorisieren: LocalName -> PeripheralName -> (unknown)
            name = adv.get(CB.CBAdvertisementDataLocalNameKey) or p.name() or "(unknown)"
            msd = adv.get(CB.CBAdvertisementDataManufacturerDataKey)
            ident = str(p.identifier())
            self.store.update(ident, name, rssi, bytes(msd) if msd else None)
        except Exception as e:
            print(f"Discover Error: {e}", file=sys.stderr)

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
                print(f"Write Error: {e}")
            time.sleep(WRITE_INTERVAL)

    def stop(self):
        self.run_flag = False

def scan_loop(store):
    delegate = CentralDelegate.alloc().initWithStore_(store)
    central = CB.CBCentralManager.alloc().initWithDelegate_queue_options_(
        delegate, None, None
    )

    rl = NSRunLoop.currentRunLoop()
    print("[LGS-Scanner] Running...")

    while True:
        try:
            rl.runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.1))
            time.sleep(SCAN_IDLE_SLEEP)
        except KeyboardInterrupt:
            break

def main():
    print("[LGS-Scanner] START")
    store = Store()
    writer = WriterThread(store)
    writer.start()

    try:
        scan_loop(store)
    finally:
        writer.stop()
        print("[LGS-Scanner] STOP")

if __name__ == "__main__":
    main()