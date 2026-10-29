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
            "left": (0.60, 0.40),
            "right": (0.30, 0.40),
            "down_left": (0.60, 0.40),
            "down_right": (0.35, 0.40),
            "up_left": (0.60, 0.40),
            "up_right": (0.35, 0.40),
        },
    },
    "bulbasaur": {
        "walk": {"cols": 6},
        "idle": {"cols": 3},
        "shoot": {"cols": 6},
        "strike": {"cols": 11},
        # Walk frames are heavily padded; keep the body narrower than a tile so
        # one-tile corridors (e.g. ladders) stay passable
        "hitbox": (36, 36),
        "mouth_fracs": {
            "down": (0.47, 0.60),
            "up": (0.50, 0.45),
            # inverted so left is when bulbasaur faces right and vice versa
            "left": (0.80, 0.55),
            "right": (0.20, 0.55),
            "down_left": (0.62, 0.66),
            "down_right": (0.36, 0.66),
            # back to the camera, so fire from the front of the body
            "up_left": (0.72, 0.42),
            "up_right": (0.28, 0.42),
        },
    },
}
