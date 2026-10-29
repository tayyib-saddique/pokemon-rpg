import random

import pygame
import pytest

from pokemon_rpg.gameplay.combat.projectiles.bullet_seed import BulletSeed
from pokemon_rpg.gameplay.combat.projectiles.ember import Ember
from pokemon_rpg.gameplay.combat.projectiles.razor_leaf import RazorLeaf

VOLLEYS = [RazorLeaf, BulletSeed]


@pytest.fixture
def player(display):
    from pokemon_rpg.gameplay.entities.player import Player

    return Player(
        (400, 400),
        pygame.sprite.Group(),
        create_projectile_callback=lambda *args: None,
        pokemon="totodile",
    )


def fire_at(cls, player, distance=80):
    # Thrown from below, travelling up into the player
    projectile = cls(
        player.hitbox.centerx,
        player.hitbox.centery + distance,
        "up",
        combat_sprites=pygame.sprite.Group(player),
    )
    group = pygame.sprite.Group(projectile)
    for _ in range(120):
        group.update(1 / 60)
    return projectile


@pytest.mark.parametrize("cls", VOLLEYS)
def test_whole_volley_lands_on_invincible_player(cls, player):
    random.seed(4)
    start = player.health.current

    fire_at(cls, player)

    assert start - player.health.current == cls.SHOT_CLASS.DAMAGE * cls.SHOT_COUNT


@pytest.mark.parametrize("cls", VOLLEYS)
def test_other_projectiles_still_blocked_after_volley(cls, player):
    random.seed(4)
    fire_at(cls, player)
    after_volley = player.health.current

    fire_at(Ember, player)

    assert player.invincible_timer > 0
    assert player.health.current == after_volley


def test_second_volley_blocked_during_first_volleys_window(player):
    random.seed(4)
    fire_at(RazorLeaf, player)
    after_first = player.health.current

    fire_at(RazorLeaf, player)

    assert player.health.current == after_first


@pytest.mark.parametrize("cls", VOLLEYS)
def test_camera_sorts_each_shot_at_its_own_depth(cls, display):
    from pokemon_rpg.rendering.camera import CameraGroup

    camera = CameraGroup()
    volley = cls(400, 400, "up")
    camera.add(volley)
    for _ in range(20):
        camera.update(1 / 60)

    _, _, depth, overlay = camera._bucket_sprites(player=None)

    assert volley not in depth and volley not in overlay
    assert set(depth) == set(volley.shots)
    # Shots fired up have moved on from the spawn point, so sort above it
    assert all(shot.ground_y < 400 for shot in volley.shots)
