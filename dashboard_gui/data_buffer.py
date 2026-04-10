import os
import json
import time
import decoder  # <- wichtig
class DataBuffer:
    def __init__(self):
        self.path = os.path.join("data", "decoded.json")
        # Wir behalten 'self.data', damit kein AttributeError kommt
        self.data = [] 

        self.file_exists = False
        self.data_ok = False
        self.alive_flag = False

    def load(self):
        # 🔥 1. RAM FIRST
        ram_data = decoder.get_decoded_ram()
    
        if ram_data:
            self.data = ram_data
            self.data_ok = True
    
            if len(self.data) > 0:
                self.alive_flag = bool(self.data[0].get("alive", False))
            else:
                self.alive_flag = False
    
            return self.data
    
        # 🔥 2. FALLBACK NUR BEIM START
        self.file_exists = os.path.exists(self.path)
    
        if not self.file_exists:
            return self.data
    
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                new_content = json.load(f)
    
            if isinstance(new_content, list):
                self.data = new_content
                self.data_ok = True
            else:
                self.data_ok = False
    
        except:
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