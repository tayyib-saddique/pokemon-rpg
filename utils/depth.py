# Depth / ground-Y helpers for tile depth sorting.

def get_depth_value(tile_y: int, tile_h: int) -> int:
    """World-pixel Y at 3/4 down a tile — used as the depth sort anchor."""
    return tile_y * tile_h + tile_h * 3 // 4


def find_tree_depth(tile_x: int, tile_y: int, base_positions: dict, fallback: int) -> int:
    """
    Walk downward from (tile_x, tile_y) to find the nearest Tree Base tile.
    Searches the same column first, then ±1 and ±2 adjacent columns to handle
    canopies that are wider than their trunk.
    """
    for dx in [0, -1, 1, -2, 2]:
        for row in range(tile_y + 1, tile_y + 15):
            if (tile_x + dx, row) in base_positions:
                return base_positions[(tile_x + dx, row)]

    return fallback


def tile_depth(x: int, y: int, tile_h: int, layer_name: str,
               base_positions: dict, fallback: int) -> int:
    """Return the correct depth sort value for a tile based on its layer name."""
    if 'Tips' in layer_name or 'Mid' in layer_name:
        return find_tree_depth(x, y, base_positions, fallback)
    return get_depth_value(y, tile_h)