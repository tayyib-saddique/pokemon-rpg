def map_connection(target_map, entry_pos):
    return {
        "map": target_map,
        "entry_pos": entry_pos,
    }


MAPS = {
    "vertia_road": {
        "path": "assets/floor_maps/vertia_road.tmx",
        "connections": {
            "north": None,
            "south": None,
            "east": None,
            "west": map_connection("vertia_city", (2817, 568)),
        },
        "enemy_spawns": [
            {
                "pokemon": "charmander",
                "pos": (700, 80),
                "tier": 1,
                "boss": False,
            },
        ],
    },
    "vertia_city": {
        "path": "assets/floor_maps/vertia_city.tmx",
        "no_combat": True,
        "connections": {
            "north": None,
            "south": None,
            "east": map_connection("vertia_road", (126, 568)),
            "west": None,
        },
    },
}


def get_connection(source_map, edge):
    return MAPS[source_map]["connections"].get(edge)
