def get_depth_value(tile_y: int, tile_h: int) -> int:
    """World-pixel Y at 3/4 down a tile, used as the depth sort anchor."""
    return tile_y * tile_h + tile_h * 3 // 4


def find_anchor_depth(
    tile_x: int,
    tile_y: int,
    anchor_positions: dict,
    fallback: int,
    foot_positions: set | None = None,
) -> int:
    """
    Walk downward (trying adjacent columns for diagonal robustness) and
    return the depth of the bottom-most tile in the contiguous run of
    anchor tiles. Used so an overlay tile (Tree Tips/Mid, Town Overlay)
    sorts at the depth of its object's foot.

    When foot_positions is given, only tiles in it can be the foot; a run
    without any (e.g. a stack of loose flowers) anchors at its top tile.
    """
    for dx in [0, -1, 1, -2, 2]:
        top_row = None
        bottom_row = None
        for row in range(tile_y, tile_y + 15):
            cell = (tile_x + dx, row)
            if cell in anchor_positions:
                if top_row is None:
                    top_row = row
                if foot_positions is None or cell in foot_positions:
                    bottom_row = row
            elif top_row is not None:
                break
        if top_row is not None:
            row = bottom_row if bottom_row is not None else top_row
            return anchor_positions[(tile_x + dx, row)]
    return fallback


def tile_depth(
    x: int,
    y: int,
    tile_h: int,
    layer_name: str,
    tree_base_positions: dict,
    town_positions: dict,
    building_foot_depths: dict,
    fallback: int,
    town_foot_positions: set | None = None,
) -> int:
    """Return the correct depth sort value for a tile based on its layer."""
    if "Tree Tips" in layer_name or "Tree Mid" in layer_name:
        return find_anchor_depth(x, y, tree_base_positions, fallback)

    if "Buildings Roof" in layer_name or layer_name in ("Buildings", "Buildings Base"):
        # Building walls and roof sort as one connected component anchored to
        # the top of its southernmost blocking row: the front/base line.
        return building_foot_depths.get((x, y), get_depth_value(y, tile_h))

    if "Town Overlay" in layer_name:
        # Overlay decorations (sign tops, awnings, etc.) sort IN FRONT of any
        # building tile they cover: nudge just past the building's foot depth.
        depth = find_anchor_depth(x, y, town_positions, fallback, town_foot_positions)
        building = building_foot_depths.get((x, y))
        if building is not None:
            return max(depth, building + 1)
        return depth

    if "Town" in layer_name:
        # Town Base decorations sort BEHIND any building tile they cover: clamp
        # just under the building's foot depth.
        depth = find_anchor_depth(x, y, town_positions, fallback, town_foot_positions)
        building = building_foot_depths.get((x, y))
        if building is not None:
            return min(depth, building - 1)
        return depth

    if "Door" in layer_name:
        # Doors sit at the building's foot; nudge +1 so they render just above
        # Building Base tiles at the same row.
        return get_depth_value(y, tile_h) + 1

    return get_depth_value(y, tile_h)
