# dashboard_gui/engines/tile_engine.py

class TileEngine:
    def __init__(self, gsm):
        self.gsm = gsm
        # REIHENFOLGE DER WAHRHEIT
        self.available_tiles = [
            "temp_in", "hum_in", "vpd_in",
            "temp_ex", "hum_ex", "vpd_ex",

            "ble_temp_sps",
            "ble_hum_sps",
            "ble_vpd_sps",
            "ble_temp_tb2",
            "ble_hum_tb2",
            "ble_vpd_tb2",
            "leaf_temp", "vpd_leaf", 
            "circulation_fan_rpm",  # NEU
            "exhaust_fan_rpm",      # NEU
            "v_bat"            ]
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
        if not self.active_tiles:
            return current_full_key

        try:
            # Wir suchen, welches Tile aus 'active_tiles' im Key steckt
            found_tile = None
            for tile in self.active_tiles:
                if current_full_key.endswith(tile):
                    found_tile = tile
                    break
            
            if not found_tile:
                # Fallback: Wenn wir das Tile nicht identifizieren können
                return current_full_key

            # Präfix isolieren (Alles vor dem Tile-Namen, inkl. dem Unterstrich davor)
            prefix = current_full_key[:-(len(found_tile) + 1)]
            
            # Index bestimmen
            idx = self.active_tiles.index(found_tile)
            new_idx = (idx + direction) % len(self.active_tiles)
            
            next_tile_id = self.active_tiles[new_idx]
            
            # Neuer Key: Präfix + Unterstrich + neues Tile
            return f"{prefix}_{next_tile_id}"
        except Exception as e:
            print(f"[TileEngine] Navigation Error: {e}")
            return current_full_key
        
# ---------------------------------------------------------
    # FULL KEY NAVIGATION
    # ---------------------------------------------------------

    def get_next_full_key(self, current_full_key, direction):
        if not self.active_tiles:
            return current_full_key

        try:
            # Wir suchen, welches Tile aus 'active_tiles' im Key steckt
            found_tile = None
            for tile in self.active_tiles:
                if current_full_key.endswith(tile):
                    found_tile = tile
                    break
            
            if not found_tile:
                # Fallback: Wenn das Tile nicht in der aktuellen Liste ist, nutze Schutzfunktion
                return self.get_safe_neighbor(current_full_key, direction)

            # Präfix isolieren (Alles vor dem Tile-Namen, inkl. dem Unterstrich davor)
            prefix = current_full_key[:-(len(found_tile) + 1)]
            
            # Index bestimmen
            idx = self.active_tiles.index(found_tile)
            new_idx = (idx + direction) % len(self.active_tiles)
            
            next_tile_id = self.active_tiles[new_idx]
            
            # Neuer Key: Präfix + Unterstrich + neues Tile
            return f"{prefix}_{next_tile_id}"
        except Exception as e:
            print(f"[TileEngine] Navigation Error: {e}")
            return current_full_key
        
    # --- JETZT KORREKT EINGERÜCKT (Klassenmethoden) ---
    def get_first_tile_key(self, dev_id, channel):
        """Gibt den vollständigen Key für das allererste gültige Tile zurück."""
        if not self.active_tiles:
            return None
        return f"{dev_id}_{channel}_{self.active_tiles[0]}"
    
    def get_safe_neighbor(self, current_key, direction):
        """Findet den Nachbarn, aber NUR innerhalb der existierenden Tiles."""
        parts = current_key.split("_")
        if len(parts) < 3:
            return current_key
            
        dev_id, channel = parts[0], parts[1]
        tile_id = "_".join(parts[2:])
        
        if not self.active_tiles:
            return current_key
            
        if tile_id not in self.active_tiles:
            return self.get_first_tile_key(dev_id, channel) or current_key
            
        idx = self.active_tiles.index(tile_id)
        new_idx = (idx + direction) % len(self.active_tiles)
        return f"{dev_id}_{channel}_{self.active_tiles[new_idx]}"   