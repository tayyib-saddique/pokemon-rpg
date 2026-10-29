import pygame
import pytest

from pokemon_rpg.data.pokemon import SPRITE_SHEETS
from pokemon_rpg.gameplay.entities.base import make_hitbox

TILE = 48  # collision tiles are 16px scaled x3


class Wall(pygame.sprite.Sprite):
    def __init__(self, rect):
        super().__init__()
        self.rect = pygame.Rect(rect)


def test_configured_hitbox_is_centred_on_sprite():
    rect = pygame.Rect(100, 100, 120, 120)

    hitbox = make_hitbox("bulbasaur", rect)

    assert hitbox.size == SPRITE_SHEETS["bulbasaur"]["hitbox"]
    assert hitbox.center == rect.center


def test_hitbox_falls_back_to_half_the_frame():
    rect = pygame.Rect(0, 0, 96, 144)

    hitbox = make_hitbox("missingno", rect)

    assert hitbox.size == (48, 72)
    assert hitbox.center == rect.center


@pytest.mark.parametrize(
    "pokemon", [p for p, data in SPRITE_SHEETS.items() if "hitbox" in data]
)
def test_configured_hitbox_fits_one_tile_corridor(pokemon):
    width, height = SPRITE_SHEETS[pokemon]["hitbox"]

    assert width < TILE and height < TILE


def test_bulbasaur_player_walks_up_one_tile_corridor(display):
    from pokemon_rpg.gameplay.entities.player import Player

    # Ladder-style gap, one tile wide, between two wall columns
    walls = pygame.sprite.Group(
        Wall((0, 200, 480, 200)),
        Wall((480 + TILE, 200, 500, 200)),
    )
    player = Player(
        (504, 500),
        pygame.sprite.Group(),
        create_projectile_callback=lambda *args: None,
        pokemon="bulbasaur",
        collision_sprites=walls,
    )
    player.input = lambda: player.direction.update(0, -1)

    for _ in range(120):
        player.update(1 / 60, [])

    assert player.hitbox.bottom < 200
