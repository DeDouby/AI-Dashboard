# data_buffer.py – erweitert für LED-Status-Flow

import os
import json

class DataBuffer:
    def __init__(self):
        self.path = os.path.join("data", "decoded.json")
        self.data = None

        # neue Felder für LED-Flow
        self.file_exists = False
        self.data_ok = False
        self.alive_flag = False

    def load(self):
        # Datei existiert?
        self.file_exists = os.path.exists(self.path)

        if not self.file_exists:
            self.data = None
            self.data_ok = False
            self.alive_flag = False
            return None

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except:
            self.data = None

        # gültige Daten?
        if isinstance(self.data, list):
            self.data_ok = True
        
            if len(self.data) > 0:
                d = self.data[0]
                self.alive_flag = bool(d.get("alive", False))
            else:
                # leere Liste = bewusst kein Frame
                self.alive_flag = False
        else:
            self.data_ok = False
            self.alive_flag = False
    def clear(self):
        """Leert den aktuellen Frame-Speicher komplett."""
        self.data = None
        self.data_ok = False
        self.alive_flag = False
        # Optional: Die Datei auf der Disk auch leeren, 
        # damit beim Neustart kein 'Müll' geladen wird
        if os.path.exists(self.path):
            try:
                with open(self.path, "w") as f:
                    f.write("[]") 
            except:
                pass
    def get(self):
        return self.data

    def soft_reload(self):
        return self.load()

# global Singleton
BUFFER = DataBuffer()
