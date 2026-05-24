def get_depth_value(tile_y: int, tile_h: int) -> int:
    """World-pixel Y at 3/4 down a tile — used as the depth sort anchor."""
    return tile_y * tile_h + tile_h * 3 // 4


def find_anchor_depth(
    tile_x: int, tile_y: int, anchor_positions: dict, fallback: int
) -> int:
    """
    Walk downward (trying adjacent columns for diagonal robustness) and
    return the depth of the bottom-most tile in the contiguous run of
    anchor tiles. Used so an overlay tile (Tree Tips/Mid, Building Roof,
    Town overlay) sorts at the depth of its object's foot.

    Starting at tile_y is safe in all three cases because the caller's
    anchor dict never contains the overlay tile's own coordinate — Tree
    Tips/Mid coords aren't in tree_base_positions, Building Roof coords
    aren't in building_base_positions, and Town tiles are their own
    anchor (they sort at the bottom of their own column).
    """
    for dx in [0, -1, 1, -2, 2]:
        bottom_row = None
        for row in range(tile_y, tile_y + 15):
            if (tile_x + dx, row) in anchor_positions:
                bottom_row = row
            elif bottom_row is not None:
                break
        if bottom_row is not None:
            return anchor_positions[(tile_x + dx, bottom_row)]
    return fallback


def tile_depth(
    x: int,
    y: int,
    tile_h: int,
    layer_name: str,
    tree_base_positions: dict,
    building_base_positions: dict,
    town_positions: dict,
    fallback: int,
) -> int:
    """Return the correct depth sort value for a tile based on its layer."""
    if "Tree Tips" in layer_name or "Tree Mid" in layer_name:
        return find_anchor_depth(x, y, tree_base_positions, fallback)

    if "Building Roof" in layer_name or "Buildings Roof" in layer_name:
        return find_anchor_depth(x, y, building_base_positions, fallback)

    if "Town" in layer_name:
        return find_anchor_depth(x, y, town_positions, fallback)

    if "Door" in layer_name:
        # Doors sit at the building's foot — nudge +1 so they render
        # just above Building Base tiles at the same row.
        return get_depth_value(y, tile_h) + 1

    return get_depth_value(y, tile_h)
