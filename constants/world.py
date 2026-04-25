MAPS = {
    "vertia_road": {
        "path": "graphics/floor_maps/vertia_road.tmx",
        "connections": {
            "north": None,
            "south": None,
            "east": None,
            "west": "vertia_city",
        },
        "enemy_spawns": [
            {
                "pokemon": "charmander",
                "pos": (700, 80),
                "tier": 1,
                "boss": False,
                "patrol_points": None,
            },
            {
                "pokemon": "charmander",
                "pos": (239, 936),
                "tier": 1,
                "boss": False,
                "patrol_points": [(239, 936), (1122, 936)],
            },
        ],
    },
    "vertia_city": {
        "path": "graphics/floor_maps/vertia_city.tmx",
        "no_combat": True,
        "connections": {
            "north": None,
            "south": None,
            "east": "vertia_road",
            "west": None,
        },
    },
}

ENTRY_POSITIONS = {
    "west": lambda p, w, h: (w - 120, p.pos.y),
    "east": lambda p, w, h: (120, p.pos.y),
    "north": lambda p, w, h: (p.pos.x, h - 120),
    "south": lambda p, w, h: (p.pos.x, 120),
}
