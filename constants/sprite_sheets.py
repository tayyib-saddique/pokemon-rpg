SPRITE_SHEETS = {
    "totodile": {
        "walk": {"cols": 4},
        "idle": {"cols": 7},
        "shoot": {"cols": 14, "trim": (2, 3, 4, 5)},
        "strike": {"cols": 9},
        "mouth_fracs": {
            "down": (0.50, 0.50),
            "up": (0.50, 0.50),
            # inverted so left is when totodile faces right and vice versa
            # slight asymmetry in sprite
            "left": (0.70, 0.40),
            "right": (0.25, 0.40),
            "down_left": (0.60, 0.40),
            "down_right": (0.40, 0.40),
            "up_left": (0.60, 0.40),
            "up_right": (0.40, 0.40),
        },
    },
    "charmander": {
        "walk": {"cols": 4},
        "idle": {"cols": 4},
        "shoot": {"cols": 10, "trim": range(2, 6)},
        "strike": {"cols": 9},
        "mouth_fracs": {
            "down": (0.50, 0.50),
            "up": (0.50, 0.50),
            # inverted so left is when charmander faces right and vice versa
            # slight asymmetry in sprite
            "left": (0.70, 0.40),
            "right": (0.25, 0.40),
            "down_left": (0.60, 0.40),
            "down_right": (0.35, 0.40),
            "up_left": (0.60, 0.40),
            "up_right": (0.35, 0.40),
        },
    },
}
