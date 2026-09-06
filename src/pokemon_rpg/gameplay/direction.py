def direction_name(dx: float, dy: float, fallback: str = "down") -> str:
    """
    Map a (dx, dy) movement vector to a facing string.
    Returns `fallback` when both components are zero.

    Snaps to the dominant cardinal axis when the minor component is less than
    half the major, so tile-centre y-offsets don't produce unwanted diagonals.
    """
    adx, ady = abs(dx), abs(dy)

    # Cardinal snap: minor axis < 50 % of major → pure horizontal / vertical
    if ady < adx * 0.5:
        return "right" if dx < 0 else "left"
    if adx < ady * 0.5:
        return "down" if dy > 0 else "up"

    # True diagonal (both axes roughly equal)
    if dx < 0 and dy > 0:
        return "down_right"
    if dx < 0 and dy < 0:
        return "up_right"
    if dx > 0 and dy > 0:
        return "down_left"
    if dx > 0 and dy < 0:
        return "up_left"

    return fallback
