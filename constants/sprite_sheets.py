_DEFAULT_MOUTH_FRACS = {
    "down": (0.50, 0.20),
    "up": (0.50, 0.20),
    "left": (0.78, 0.40),
    "right": (0.22, 0.40),
    "down_left": (0.20, 0.25),
    "down_right": (0.80, 0.25),
    "up_left": (0.35, 0.50),
    "up_right": (0.65, 0.50),
}

SPRITE_SHEETS = {
    "totodile": {
        "walk": {"cols": 4},
        "idle": {"cols": 7},
        "shoot": {"cols": 14, "trim": (2, 3, 4, 5)},
        "strike": {"cols": 9},
        "mouth_fracs": _DEFAULT_MOUTH_FRACS,
    },
    "charmander": {
        "walk": {"cols": 4},
        "idle": {"cols": 4},
        "shoot": {"cols": 10, "trim": range(2, 6)},
        "strike": {"cols": 9},
        "mouth_fracs": _DEFAULT_MOUTH_FRACS,
    },
}
