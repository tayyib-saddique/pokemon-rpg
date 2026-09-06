from types import SimpleNamespace

import pygame

from pokemon_rpg.world.navigation import NavGrid


def test_finds_path_between_walkable_cells():
    nav = NavGrid([], map_width=48, map_height=48, tile_size=16)
    path = nav.find_path((8, 8), (40, 40))

    assert path[0] == (8, 8)
    assert path[-1] == (40, 40)


def test_moves_blocked_endpoint_to_nearest_walkable_cell():
    obstacle = SimpleNamespace(rect=pygame.Rect(16, 16, 16, 16))
    nav = NavGrid([obstacle], map_width=48, map_height=48, tile_size=16)
    path = nav.find_path((8, 8), (24, 24))

    assert path
    assert path[-1] != (24, 24)


def test_out_of_bounds_endpoints_are_clamped():
    nav = NavGrid([], map_width=48, map_height=48, tile_size=16)
    path = nav.find_path((-100, -100), (1000, 1000))

    assert path[0] == (8, 8)
    assert path[-1] == (40, 40)
