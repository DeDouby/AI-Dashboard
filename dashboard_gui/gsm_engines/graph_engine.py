import config
from collections import defaultdict, deque

class GraphEngine:
    def __init__(self, gsm):
        self.gsm = gsm
        self.running = True
      
        # Buffers
        self.window = config.get_tile_graph_window()
        self.graph_buffers = defaultdict(self._new_buffer)
        self._trend_buffers = defaultdict(self._new_buffer)
        self._last_smoothed_values = {}
        self._last_units = {}  # NEU: Speichert die Einheit des letzten Wertes
        # Trends
        self.global_trends = {}
        
        # Settings
        self.smoothing_factor = 0.1

    def _new_buffer(self):
        return deque(maxlen=self.window)
    # ---------------------------------------------------------
    # DATA ACCESS (Wichtig für Mixed Mode & Tiles)
    # ---------------------------------------------------------
    def get_last_value(self, key):
        """Liefert den aktuellsten Wert aus dem Puffer für die UI."""
        buf = self.graph_buffers.get(key)
        if buf and len(buf) > 0:
            return buf[-1]
        return None

    def get_buffer(self, key):
        """Liefert Liste für Kivy Graph. Wenn leer, gib leere Liste zurück."""
        buf = self.graph_buffers.get(key)
        return list(buf) if buf else [] # KEINE 0.0 DUMMY PUNKTE MEHR!
    def get_stats(self, key):
        """Liefert avg / min / max eines Graphbuffers mit Crash-Schutz."""
        buf = self.graph_buffers.get(key)
    
        if not buf or len(buf) < 2:
            return None, None, None
    
        data = list(buf)
        avg = sum(data) / len(data)
        mn = min(data)
        mx = max(data)
    
        # 🔥 DER FIX: Verhindert ZeroDivisionError in Kivy-Garden Graph
        if mn == mx:
            # Wenn die Werte gleich sind (z.B. Fan steht auf 800 RPM)
            # geben wir dem Graphen einen winzigen Spielraum zum Rechnen
            mn -= 0.1
            mx += 0.1
    
        return avg, mn, mx
    def get_trend_icon(self, key):
        """Liefert FontAwesome Icon."""
        val = self.global_trends.get(key, 0)
        icons = {-1: "\uf063", 1: "\uf062", 0: "\uf061"}
        return icons.get(val, "\uf061")


    def get_all_keys(self):
        """Liefert alle aktuell existierenden Keys im Buffer."""
        return list(self.graph_buffers.keys())
    # ---------------------------------------------------------
    # PROCESS VALUE
    # ---------------------------------------------------------
    def process_new_value(self, key, value):
        if not self.running or value is None:
            return
            
        try:
            val_float = float(value)
            current_unit = self.gsm.get_unit(key)
            
            # löschen wir den Puffer für diesen Key, damit es keinen Peak gibt.
# --- UNIT SWITCH LOGIK ---
            if key in self._last_units and self._last_units[key] != current_unit:
                print(f"[GraphEngine] Unit switch... Resetting buffer for {key}")
                
                # Wir löschen nicht nur, wir initialisieren SOFORT mit zwei validen Punkten
                # Damit len(buf) niemals 0 oder 1 ist, wenn die UI zugreift.
                self.graph_buffers[key] = deque([val_float, val_float], maxlen=self.window)
                self._trend_buffers[key] = deque([val_float, val_float], maxlen=self.window)
                self._last_smoothed_values[key] = val_float
                self._last_units[key] = current_unit
                return # In diesem Durchlauf fertig, Struktur ist sicher
            # --- 1. SMOOTHING LOGIK ---
            # TIPP: Mixed-Werte sind schon berechnet, hier Smoothing fast deaktivieren
            f = 0.8 if "mixed" in key else self.smoothing_factor
            
            if key not in self._last_smoothed_values:
                smoothed = val_float
            else:
                last = self._last_smoothed_values[key]
                # DRIFT-CHECK: Bei Sprüngen > 5.0 sofort springen
                if abs(val_float - last) > 5.0:
                    smoothed = val_float
                else:
                    smoothed = (last * (1 - f)) + (val_float * f)
            
            self._last_smoothed_values[key] = smoothed
            
            # --- 2. PUFFER BEFÜLLEN ---
            g_buf = self.graph_buffers[key]
            g_buf.append(smoothed)
            if len(g_buf) > self.window:
                g_buf.popleft()
            
            t_buf = self._trend_buffers[key]
            t_buf.append(smoothed)
            if len(t_buf) > self.window:
                t_buf.popleft()
                
            # --- 3. TREND BERECHNEN ---
            self.global_trends[key] = self._calculate_trend_logic(list(t_buf))
            
        except Exception as e:
            print(f"[GraphEngine] Error in process_new_value: {e}")

    def _calculate_trend_logic(self, buf):
        if len(buf) < 5: return 0
        start, end = buf[0], buf[-1]
        diff = end - start
        threshold = max(0.01, abs(start) * 0.002)
        
        if diff > threshold: return 1
        if diff < -threshold: return -1
        return 0

    def reset(self):
        print("[GraphEngine] RESET")
        self.graph_buffers.clear()
        self._trend_buffers.clear()
        self._last_smoothed_values.clear()
        self.global_trends.clear()

    def rebuild_buffers(self):
        """Rebuild deque buffers after the config window changes."""
        self.window = config.get_tile_graph_window()
        for key in list(self.graph_buffers.keys()):
            old_buf = list(self.graph_buffers[key])[-self.window:]
            self.graph_buffers[key] = deque(old_buf, maxlen=self.window)
        for key in list(self._trend_buffers.keys()):
            old_buf = list(self._trend_buffers[key])[-self.window:]
            self._trend_buffers[key] = deque(old_buf, maxlen=self.window)

    def refresh_config(self):
        self.rebuild_buffers()