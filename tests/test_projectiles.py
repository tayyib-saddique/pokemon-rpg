import pygame
import pytest

from pokemon_rpg.gameplay.combat.projectiles.base import (
    BaseProjectile,
    FACING_VELOCITY,
)
from pokemon_rpg.gameplay.direction import direction_name


class ProjectileStub(BaseProjectile):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rect = pygame.Rect(0, 0, 4, 4)
        self.rect.center = self.pos

    def draw(self, surface, offset=(0, 0)):
        pass


class DamageTarget(pygame.sprite.Sprite):
    def __init__(self, centre):
        super().__init__()
        self.rect = pygame.Rect(0, 0, 8, 8)
        self.rect.center = centre
        self.damage_taken = 0

    def take_damage(self, amount):
        self.damage_taken += amount


@pytest.mark.parametrize(
    "movement",
    [
        (0, -1),
        (0, 1),
        (-1, 0),
        (1, 0),
        (-1, -1),
        (1, -1),
        (-1, 1),
        (1, 1),
    ],
)
def test_facing_conversion_preserves_movement_direction(movement):
    facing = direction_name(*movement)
    velocity = FACING_VELOCITY[facing]
    velocity_sign = tuple(
        0 if value == 0 else int(value / abs(value)) for value in velocity
    )

    assert velocity_sign == movement


def test_projectile_expires_after_maximum_range():
    group = pygame.sprite.Group()
    projectile = ProjectileStub(10, 10, "left", speed=10, max_range=5)
    group.add(projectile)

    projectile.update(1.0)

    assert not projectile.active
    assert projectile not in group


def test_projectile_damages_target_once_then_dies():
    target = DamageTarget((20, 10))
    projectile = ProjectileStub(
        10,
        10,
        "left",
        speed=10,
        combat_sprites=pygame.sprite.Group(target),
    )

    projectile.update(1.0)
    projectile.update(1.0)

    assert target.damage_taken == 10
    assert not projectile.active


def test_projectile_expires_outside_map():
    projectile = ProjectileStub(
        5, 5, "right", speed=10, map_size=(20, 20), max_range=100
    )

    projectile.update(1.0)

    assert not projectile.active
