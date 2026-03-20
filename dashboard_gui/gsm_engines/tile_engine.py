# dashboard_gui/engines/tile_engine.py

class TileEngine:

    def __init__(self, gsm):

        self.gsm = gsm

        # bekannte Tile IDs (metriken)
        self.available_tiles = [
            "temp_in",
            "hum_in",
            "vpd_in",
            "temp_ex",
            "hum_ex",
            "leaf_temp",  # NEU
            "v_bat"       # NEU    
            "vpd_ex"
        
        ]


        # aktuell aktive Tiles (UI synchronisiert diese)
        self.active_tiles = []

    # ---------------------------------------------------------
    # UI REGISTRATION
    # ---------------------------------------------------------

    def register_tiles(self, tile_ids):
        """MetricsEngine meldet, was wirklich an Sensoren da ist."""
        self.active_tiles = list(tile_ids) if tile_ids else []

        # Reihenfolge behalten
        self.active_tiles = list(tile_ids)

    def get_active_tiles(self):
        return self.active_tiles

    # ---------------------------------------------------------
    # FULL KEY BUILDER
    # ---------------------------------------------------------

    def build_full_key(self, device_id, channel, tile_id):
        return f"{device_id}_{channel}_{tile_id}"

    # ---------------------------------------------------------
    # TILE NAVIGATION
    # ---------------------------------------------------------

    def get_next_tile(self, current_tile, direction):

        if not self.active_tiles:
            return current_tile

        try:
            idx = self.active_tiles.index(current_tile)
        except ValueError:
            return current_tile

        new_idx = (idx + direction) % len(self.active_tiles)

        return self.active_tiles[new_idx]

    # ---------------------------------------------------------
    # FULL KEY NAVIGATION
    # ---------------------------------------------------------

    def get_next_full_key(self, current_full_key, direction):
        """
        Idiotensicher: Zerlegt den Key, sucht den Nachbarn in der 'Wahrheit'
        und baut den neuen Key zusammen.
        """
        if not self.active_tiles:
            return current_full_key

        try:
            parts = current_full_key.split("_")
            dev_id = parts[0]
            channel = parts[1]
            current_tile_id = "_".join(parts[2:])
            
            # Index in der Liste der Wahrheit finden
            if current_tile_id in self.active_tiles:
                idx = self.active_tiles.index(current_tile_id)
                new_idx = (idx + direction) % len(self.active_tiles)
            else:
                # Falls wir auf einem Tile sind, das gerade verschwunden ist
                new_idx = 0
            
            next_tile_id = self.active_tiles[new_idx]
            return f"{dev_id}_{channel}_{next_tile_id}"
        except:
            return current_full_key
        
        def get_first_tile_key(self, dev_id, channel):
            """Gibt den vollständigen Key für das allererste gültige Tile zurück."""
            if not self.active_tiles:
                return None
            # active_tiles wurde gerade von MetricsEngine befüllt (z.B. ["temp_in", "hum_in"])
            return f"{dev_id}_{channel}_{self.active_tiles[0]}"
        
        def get_safe_neighbor(self, current_key, direction):
            """Findet den Nachbarn, aber NUR innerhalb der existierenden Tiles."""
            parts = current_key.split("_")
            dev_id, channel = parts[0], parts[1]
            tile_id = "_".join(parts[2:])
            
            if tile_id not in self.active_tiles:
                return self.get_first_tile_key(dev_id, channel)
                
            idx = self.active_tiles.index(tile_id)
            new_idx = (idx + direction) % len(self.active_tiles)
            return f"{dev_id}_{channel}_{self.active_tiles[new_idx]}"        