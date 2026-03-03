import config
from collections import defaultdict, deque

class GraphEngine:
    def __init__(self, gsm):
        self.gsm = gsm
        self.running = True
      
        # Buffers
        self.graph_buffers = defaultdict(lambda: deque())
        self._trend_buffers = defaultdict(lambda: deque())
        self._last_smoothed_values = {}
        
        # Trends
        self.global_trends = {}
        
        # Settings
        self.smoothing_factor = 0.1
        self.window = config.get_tile_graph_window()

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
        """Liefert Liste für Kivy Graph."""
        buf = self.graph_buffers.get(key)
        return list(buf) if buf else []

    def get_trend_icon(self, key):
        """Liefert FontAwesome Icon."""
        val = self.global_trends.get(key, 0)
        icons = {-1: "\uf063", 1: "\uf062", 0: "\uf061"}
        return icons.get(val, "\uf061")

    # ---------------------------------------------------------
    # PROCESS VALUE
    # ---------------------------------------------------------
    def process_new_value(self, key, value):
        if not self.running or value is None:
            return
            
        try:
            val_float = float(value)
            
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

    # ---------------------------------------------------------
    # CONTROLS
    # ---------------------------------------------------------
    def start(self): self.running = True
    def stop(self): self.running = False
    
    def reset(self):
        print("[GraphEngine] RESET")
        self.graph_buffers.clear()
        self._trend_buffers.clear()
        self._last_smoothed_values.clear()
        self.global_trends.clear()

    def refresh_config(self):
        self.window = config.get_tile_graph_window()
        for key in self.graph_buffers:
            if len(self.graph_buffers[key]) > self.window:
                self.graph_buffers[key] = deque(list(self.graph_buffers[key])[-self.window:])