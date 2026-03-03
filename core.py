# core.py – FINAL (stabil)
# © 2025 Dominik Rosenthal

import os
from kivy.utils import platform as kivy_platform

import config
from bridge_manager import get_bridge
from watchdog_manager import DumpWatchdog
from decoder import start_decoder_thread, update_bridge_state

# ------------------------------------------------------------
# 🔥 100 % zuverlässige Android-Erkennung
# ------------------------------------------------------------
def is_android():
    if "ANDROID_ROOT" in os.environ:
        return True
    return kivy_platform == "android"


# globale Instanzen
_bridge = None
_watchdog = None


# ------------------------------------------------------------
# Watchdog Callback
# ------------------------------------------------------------
def _wd_callback(status):
    print(f"[Core] Watchdog: {status['status']} | alive={status['alive']} | last_seen={status['last_seen']}")

    update_bridge_state(
        alive=status["alive"],
        status=status["status"],
        last_seen=status["last_seen"]
    )
# ------------------------------------------------------------
# decoded.json löschen
# ------------------------------------------------------------
def _cleanup_decoded():
    try:
        path = os.path.join(config.DATA, "decoded.json")
        if os.path.exists(path):
            os.remove(path)
            print("[Core] decoded.json entfernt")
    except:
        pass

# ------------------------------------------------------------
# ble_log_dump.json löschen / clean
# ------------------------------------------------------------
def _cleanup_ble_log_dump():
    try:
        import json
        path = os.path.join(config.DATA, "ble_log_dump.json")

        with open(path, "w", encoding="utf-8") as f:
            json.dump([], f)

        print(f"[Core] ble_log_dump.json geleert: {path}")

    except Exception as e:
        print("[Core] ble_log_dump cleanup failed:", e)


def _cleanup_ble_dump():
    try:
        import json
        path = os.path.join(config.DATA, "ble_dump.json")

        with open(path, "w", encoding="utf-8") as f:
            json.dump([], f)

        print(f"[Core] ble_dump.json geleert: {path}")

    except Exception as e:
        print("[Core] ble_dump cleanup failed:", e)
# ------------------------------------------------------------
# START – von main.py
# ------------------------------------------------------------
def start():
    global _bridge, _watchdog

    print("[Core] Starte Core…")
    print("[Core] is_android():", is_android())

    _cleanup_decoded()
    _cleanup_ble_dump()
    _cleanup_ble_log_dump() 
    # -----------------------------------------------------
    # Bridge starten
    # -----------------------------------------------------
    if is_android():
        try:
            from permission_fix import check_permissions
            check_permissions()
        except:
            print("[Core] Permission check skipped")

        _bridge = get_bridge(prefer_mock=False)
        
        _bridge.start()
        _bridge.start_broadcast()
        
        print("[Core] Android-Bridges gestartet (ADV + GATT + BROADCAST)")

    # -----------------------------------------------------
    # Decoder starten (liefert decoded.json)
    # -----------------------------------------------------
    start_decoder_thread(config.get_refresh_interval())
    print("[Core] Decoder-Thread gestartet")

    # -----------------------------------------------------
    # Watchdog starten
    # -----------------------------------------------------
    _watchdog = DumpWatchdog(
        timeout=config.get_stale_timeout(),
        interval=config.get_refresh_interval(),
        callback=_wd_callback
    )
    _watchdog.start()
    print("[Core] Watchdog gestartet")

    print("[Core] System läuft.")


_broadcast_active = True  # Da sie beim start() mit gestartet wird

def is_broadcast_active():
    return _broadcast_active

def toggle_broadcast():
    global _broadcast_active
    if _broadcast_active:
        stop_broadcast_bridge()
        _broadcast_active = False
    else:
        start_broadcast_bridge()
        _broadcast_active = True
    return _broadcast_active
# ------------------------------------------------------------
# ADV ONLY
# ------------------------------------------------------------
def restart_adv_bridge():
    from kivy.clock import Clock
    if not is_android():
        return
    Clock.schedule_once(_restart_adv_safe, 0)

def _restart_adv_safe(dt):
    global _bridge
    try:
        _bridge = get_bridge()        # 🔒 IMMER neu holen
        try:
            _bridge.stop_adv()        # darf scheitern
        except Exception:
            pass

        _bridge.start_adv()           # MUSS laufen
        print("[Core] ADV Bridge restarted")

    except Exception as e:
        print("[Core] ADV restart failed:", e)

# LogBridge

def start_log_bridge():
    from kivy.clock import Clock
    if not is_android():
        return
    Clock.schedule_once(_start_log_safe, 0)

def _start_log_safe(dt):
    global _bridge
    try:
        _bridge = get_bridge()
        _bridge.start_log()
        print("[Core] LOG Bridge started")
    except Exception as e:
        print("[Core] LOG start failed:", e)


def stop_log_bridge():
    from kivy.clock import Clock
    if not is_android():
        return
    Clock.schedule_once(_stop_log_safe, 0)

def _stop_log_safe(dt):
    global _bridge
    try:
        _bridge = get_bridge()
        _bridge.stop_log()
        print("[Core] LOG Bridge stopped")
    except Exception as e:
        print("[Core] LOG stop failed:", e)



# ------------------------------------------------------------
# GATT ONLY – Stop
# ------------------------------------------------------------
def stop_gatt_bridge():
    from kivy.clock import Clock
    if not is_android():
        return
    Clock.schedule_once(_stop_gatt_safe, 0)

def _stop_gatt_safe(dt):
    global _bridge
    try:
        _bridge = get_bridge()        # 🔒 Immer frische Instanz
        _bridge.stop_gatt()
        print("[Core] GATT Bridge stopped")
    except Exception as e:
        print("[Core] GATT stop failed:", e)
# ------------------------------------------------------------
# GATT ONLY
# ------------------------------------------------------------
def restart_gatt_bridge():
    from kivy.clock import Clock
    if not is_android():
        return
    Clock.schedule_once(_restart_gatt_safe, 0)

def _restart_gatt_safe(dt):
    global _bridge
    try:
        _bridge = get_bridge()        # 🔒 IMMER neu holen
        try:
            _bridge.stop_gatt()
        except Exception:
            pass

        _bridge.start_gatt()
        print("[Core] GATT Bridge restarted")

    except Exception as e:
        print("[Core] GATT restart failed:", e)
# ------------------------------------------------------------
# LEGACY / BOTH
# ------------------------------------------------------------
def restart_bridge():
    from kivy.clock import Clock
    if not is_android():
        return
    Clock.schedule_once(_restart_bridge_safe, 0)

def _restart_bridge_safe(dt):
    global _bridge
    try:
        _bridge = get_bridge()        # 🔒 neu holen

        try:
            _bridge.stop()
        except Exception:
            pass

        _bridge.start()
        print("[Core] ADV + GATT Bridges restarted")

    except Exception as e:
        print("[Core] Bridge restart failed:", e)

# ------------------------------------------------------------
# LOG ONLY – Restart Semantik
# ------------------------------------------------------------
def restart_log_bridge():
    from kivy.clock import Clock
    if not is_android():
        return
    Clock.schedule_once(_restart_log_safe, 0)

def _restart_log_safe(dt):
    global _bridge
    try:
        _bridge = get_bridge()  # 🔒 Immer neu holen

        try:
            _bridge.stop_log()  # darf fehlschlagen, wenn nicht läuft
        except Exception:
            pass

        _bridge.start_log()  # MUSS laufen
        print("[Core] LOG Bridge restarted")

    except Exception as e:
        print("[Core] LOG restart failed:", e)
# ------------------------------------------------------------
# LOG ONLY – Stop
# ------------------------------------------------------------
def stop_log_bridge():
    from kivy.clock import Clock
    if not is_android():
        return
    Clock.schedule_once(_stop_log_safe, 0)

def _stop_log_safe(dt):
    global _bridge
    try:
        _bridge = get_bridge()        # 🔒 Immer frische Instanz
        _bridge.stop_log()
        print("[Core] LOG Bridge stopped")
    except Exception as e:
        print("[Core] LOG stop failed:", e)
# ------------------------------------------------------------
# ADV ONLY – Stop
# ------------------------------------------------------------
def stop_adv_bridge():
    from kivy.clock import Clock
    if not is_android():
        return
    Clock.schedule_once(_stop_adv_safe, 0)

def _stop_adv_safe(dt):
    global _bridge
    try:
        _bridge = get_bridge()        # 🔒 Immer frische Instanz
        _bridge.stop_adv()
        print("[Core] ADV Bridge stopped")
    except Exception as e:
        print("[Core] ADV stop failed:", e)

# ------------------------------------------------------------
# BROADCAST ONLY – Start / Stop / Restart
# ------------------------------------------------------------

def start_broadcast_bridge():
    from kivy.clock import Clock
    if not is_android():
        return
    Clock.schedule_once(_start_broadcast_safe, 0)

def _start_broadcast_safe(dt):
    global _bridge
    try:
        _bridge = get_bridge()
        _bridge.start_broadcast()
        print("[Core] BROADCAST Bridge started")
    except Exception as e:
        print("[Core] BROADCAST start failed:", e)


def stop_broadcast_bridge():
    from kivy.clock import Clock
    if not is_android():
        return
    Clock.schedule_once(_stop_broadcast_safe, 0)

def _stop_broadcast_safe(dt):
    global _bridge
    try:
        _bridge = get_bridge()
        _bridge.stop_broadcast()
        print("[Core] BROADCAST Bridge stopped")
    except Exception as e:
        print("[Core] BROADCAST stop failed:", e)


def restart_broadcast_bridge():
    from kivy.clock import Clock
    if not is_android():
        return
    Clock.schedule_once(_restart_broadcast_safe, 0)

def _restart_broadcast_safe(dt):
    global _bridge
    try:
        _bridge = get_bridge()
        try:
            _bridge.stop_broadcast()
        except:
            pass
        _bridge.start_broadcast()
        print("[Core] BROADCAST Bridge restarted")
    except Exception as e:
        print("[Core] BROADCAST restart failed:", e)
# ------------------------------------------------------------
# STOP
# ------------------------------------------------------------
def stop():
    global _bridge, _watchdog

    print("[Core] Stoppe System…")

    try:
        if _watchdog:
            _watchdog.stop()
            print("[Core] Watchdog gestoppt")
    except:
        pass

    try:
        if is_android() and _bridge:
            _bridge.stop()
            print("[Core] Bridge gestoppt")
    except:
        pass

    print("[Core] Shutdown abgeschlossen.")
