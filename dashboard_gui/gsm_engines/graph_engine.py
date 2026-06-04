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
        self._last_units = {}  
        
        # Counter für das Downsampling (Graph Resolution)
        self._update_counters = defaultdict(int)
        
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
        buf = self.graph_buffers.get(key)
        if buf and len(buf) > 0:
            return buf[-1]
        return None

    def get_buffer(self, key):
        buf = self.graph_buffers.get(key)
        return list(buf) if buf else []

    def get_stats(self, key):
        buf = self.graph_buffers.get(key)
        if not buf or len(buf) < 2:
            return None, None, None
    
        data = list(buf)
        avg = sum(data) / len(data)
        mn = min(data)
        mx = max(data)
    
        if mn == mx:
            mn -= 0.1
            mx += 0.1
    
        return avg, mn, mx

    def get_trend_icon(self, key):
        val = self.global_trends.get(key, 0)
        icons = {-1: "\uf063", 1: "\uf062", 0: "\uf061"}
        return icons.get(val, "\uf061")

    def get_all_keys(self):
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
            
            # --- UNIT SWITCH LOGIK ---
            if key in self._last_units and self._last_units[key] != current_unit:
                print(f"[GraphEngine] Unit switch... Resetting buffer for {key}")
                self.graph_buffers[key] = deque([val_float, val_float], maxlen=self.window)
                self._trend_buffers[key] = deque([val_float, val_float], maxlen=self.window)
                self._last_smoothed_values[key] = val_float
                self._last_units[key] = current_unit
                self._update_counters[key] = 0
                return
            
            # --- 1. SMOOTHING LOGIK ---
            f = 0.8 if "mixed" in key else self.smoothing_factor
            
            if key not in self._last_smoothed_values:
                smoothed = val_float
            else:
                last = self._last_smoothed_values[key]
                if abs(val_float - last) > 5.0:
                    smoothed = val_float
                else:
                    smoothed = (last * (1 - f)) + (val_float * f)
            
            self._last_smoothed_values[key] = smoothed
            
            # --- 2. GRAPH RESOLUTION LOGIK (Slider: 1-100) ---
            raw_res = float(config.get_graph_resolution())
            
            # Sicherheitsnetz für alte Float-Reste (z.B. 0.01 -> 1, 1.0 -> 100)
            if raw_res <= 1.0:
                res_percent = max(1.0, raw_res * 100.0)
            else:
                res_percent = raw_res
                
            if res_percent < 1: res_percent = 1.0
            if res_percent > 100: res_percent = 100.0

            # Umkehrung: 1% skippt maximal (Intervall 100), 100% skippt gar nicht (Intervall 1)
            skip_interval = int(100.0 / res_percent)
            if skip_interval < 1:
                skip_interval = 1
            
            self._update_counters[key] += 1
            
            # Nur in den Buffer schreiben, wenn das Intervall erreicht ist
            if self._update_counters[key] >= skip_interval:
                self._update_counters[key] = 0  
                
                # Puffer befüllen
                g_buf = self.graph_buffers[key]
                g_buf.append(smoothed)
                if len(g_buf) > self.window:
                    g_buf.popleft()
                
                t_buf = self._trend_buffers[key]
                t_buf.append(smoothed)
                if len(t_buf) > self.window:
                    t_buf.popleft()
                    
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
        self._update_counters.clear()

    def rebuild_buffers(self):
        self.window = config.get_tile_graph_window()
        for key in list(self.graph_buffers.keys()):
            old_buf = list(self.graph_buffers[key])[-self.window:]
            self.graph_buffers[key] = deque(old_buf, maxlen=self.window)
        for key in list(self._trend_buffers.keys()):
            old_buf = list(self._trend_buffers[key])[-self.window:]
            self._trend_buffers[key] = deque(old_buf, maxlen=self.window)

    def refresh_config(self):
        self.rebuild_buffers()