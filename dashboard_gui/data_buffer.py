import os
import json
import time

class DataBuffer:
    def __init__(self):
        self.path = os.path.join("data", "decoded.json")
        # Wir behalten 'self.data', damit kein AttributeError kommt
        self.data = [] 

        self.file_exists = False
        self.data_ok = False
        self.alive_flag = False

    def load(self):
        self.file_exists = os.path.exists(self.path)

        if not self.file_exists:
            # Wenn Datei weg, behalten wir den RAM-Stand (self.data) einfach bei
            return self.data

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                new_content = json.load(f)
                
            # Validitäts-Check: Nur überschreiben, wenn wir echtes JSON haben
            if isinstance(new_content, list):
                self.data = new_content
                self.data_ok = True
                
                if len(self.data) > 0:
                    self.alive_flag = bool(self.data[0].get("alive", False))
                else:
                    self.alive_flag = False
            else:
                self.data_ok = False

        except (json.JSONDecodeError, IOError, PermissionError):
            # Falls Datei gesperrt oder kaputt: Nichts tun! 
            # self.data behält den alten Stand -> KEIN FLACKERN
            self.data_ok = False 
            
        return self.data

    def get(self):
        return self.data

    def soft_reload(self):
        return self.load()

    def clear(self):
        self.data = []
        self.data_ok = False
        self.alive_flag = False
        if os.path.exists(self.path):
            try:
                with open(self.path, "w") as f:
                    f.write("[]") 
            except:
                pass

# global Singleton
BUFFER = DataBuffer()