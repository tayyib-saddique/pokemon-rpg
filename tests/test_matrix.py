from types import SimpleNamespace

import pygame

from pokemon_rpg.world.matrix import (
    build_collision_matrix,
    grid_to_world,
    world_to_grid,
)


def test_coordinate_conversion_uses_cell_centres():
    assert world_to_grid((31, 32), 16) == (1, 2)
    assert grid_to_world((1, 2), 16) == (24, 40)


def test_rect_marks_every_cell_it_overlaps():
    obstacle = SimpleNamespace(rect=pygame.Rect(8, 8, 24, 24))
    matrix = build_collision_matrix([obstacle], 48, 48, 16)

    assert matrix == [
        [0, 0, 1],
        [0, 0, 1],
        [1, 1, 1],
    ]


def test_obstacles_are_clipped_to_map_bounds():
    obstacle = SimpleNamespace(rect=pygame.Rect(-8, -8, 16, 16))
    matrix = build_collision_matrix([obstacle], 32, 32, 16)

    assert matrix == [[0, 1], [1, 1]]
