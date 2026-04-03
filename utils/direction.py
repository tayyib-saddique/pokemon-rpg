"""
Direction name resolution from a movement vector.
Pure function — no pygame state, no class required.
"""


def direction_name(dx: float, dy: float, fallback: str = "down") -> str:
    """
    Map a (dx, dy) movement vector to a facing string.
    Returns `fallback` when both components are zero.
    """
    if dx < 0 and dy > 0:
        return "down_right"
    if dx < 0 and dy < 0:
        return "up_right"
    if dx > 0 and dy > 0:
        return "down_left"
    if dx > 0 and dy < 0:
        return "up_left"
    if dy > 0:
        return "down"
    if dy < 0:
        return "up"
    if dx < 0:
        return "right"
    if dx > 0:
        return "left"
    return fallback
