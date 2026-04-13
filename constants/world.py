MAPS = {
    "vertia_road": {
        "path": "graphics/floor_maps/vertia_road.tmx",
        "connections": {
            "north": None,
            "south": None,
            "east": None,
            "west": "vertia_city",
        },
    },
    "vertia_city": {
        "path": "graphics/floor_maps/vertia_city.tmx",
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
