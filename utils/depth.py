def get_depth_value(tile_y: int, tile_h: int) -> int:
    """World-pixel Y at 3/4 down a tile — used as the depth sort anchor."""
    return tile_y * tile_h + tile_h * 3 // 4


def find_tree_depth(
    tile_x: int, tile_y: int, base_positions: dict, fallback: int
) -> int:
    """Walk downward to find the nearest Tree Base tile."""
    for dx in [0, -1, 1, -2, 2]:
        for row in range(tile_y + 1, tile_y + 15):
            if (tile_x + dx, row) in base_positions:
                return base_positions[(tile_x + dx, row)]
    return fallback


def find_building_depth(
    tile_x: int, tile_y: int, building_base_positions: dict, fallback: int
) -> int:
    """
    Walk downward from a Building Tips tile to find the bottom-most
    Building Base tile in the same column. This makes the roof sort at
    the depth of the building's foot — so it always renders above a
    player standing in front of the building.
    """
    for dx in [0, -1, 1, -2, 2]:
        bottom_row = None
        for row in range(tile_y + 1, tile_y + 15):
            if (tile_x + dx, row) in building_base_positions:
                bottom_row = row
            elif bottom_row is not None:
                break  # walked past the last base tile in this column
        if bottom_row is not None:
            return building_base_positions[(tile_x + dx, bottom_row)]
    return fallback


def tile_depth(
    x: int,
    y: int,
    tile_h: int,
    layer_name: str,
    tree_base_positions: dict,
    building_base_positions: dict,
    fallback: int,
) -> int:
    """Return the correct depth sort value for a tile based on its layer."""
    if "Tree Tips" in layer_name or "Tree Mid" in layer_name:
        return find_tree_depth(x, y, tree_base_positions, fallback)

    if "Building Tips" in layer_name:
        return find_building_depth(x, y, building_base_positions, fallback)

    if "Door" in layer_name:
        # Doors sit at the building's foot — nudge +1 so they render
        # just above Building Base tiles at the same row.
        return get_depth_value(y, tile_h) + 1

    return get_depth_value(y, tile_h)
