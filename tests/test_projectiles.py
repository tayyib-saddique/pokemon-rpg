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

    def take_damage(self, amount, source=None):
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


class Wall(pygame.sprite.Sprite):
    def __init__(self, rect):
        super().__init__()
        self.rect = pygame.Rect(rect)


def run(projectile, seconds, fps=60):
    group = pygame.sprite.Group(projectile)
    for _ in range(int(seconds * fps)):
        group.update(1 / fps)
    return group


def test_projectile_respects_map_size():
    projectile = ProjectileStub(
        1500, 10, "left", speed=10, map_size=(3000, 3000), max_range=100
    )

    projectile.update(1.0)

    assert projectile.active


def test_projectile_hits_target_hitbox_not_image_rect():
    target = DamageTarget((30, 10))
    target.hitbox = pygame.Rect(0, 0, 2, 2)
    target.hitbox.center = (60, 60)
    projectile = ProjectileStub(
        10,
        10,
        "left",
        speed=20,
        combat_sprites=pygame.sprite.Group(target),
    )

    projectile.update(1.0)

    assert target.damage_taken == 0


def test_spawn_overlap_ignores_wall_beside_path():
    # Wall runs alongside the flight path, clipped by the projectile's edge
    wall = Wall((0, 11, 200, 10))
    projectile = ProjectileStub(
        10, 10, "left", speed=10, collision_sprites=pygame.sprite.Group(wall)
    )

    projectile.update(0.5)

    assert projectile.active


def test_point_blank_wall_ahead_still_blocks():
    wall = Wall((11, 0, 4, 20))
    projectile = ProjectileStub(
        10, 10, "left", speed=10, collision_sprites=pygame.sprite.Group(wall)
    )

    projectile.update(0.1)

    assert not projectile.active


def test_ember_burst_plays_after_impact():
    from pokemon_rpg.gameplay.combat.projectiles.ember import Ember

    wall = Wall((140, 90, 32, 32))
    ember = Ember(100, 100, "left", collision_sprites=pygame.sprite.Group(wall))
    group = run(ember, 0.1)

    assert not ember.active
    assert ember.burst
    assert ember in group

    run(ember, 1.0)
    assert ember not in group


def test_flamethrower_damages_target_and_is_removed():
    from pokemon_rpg.gameplay.combat.projectiles.flamethrower import Flamethrower

    target = DamageTarget((160, 100))
    target.rect.inflate_ip(40, 40)
    flame = Flamethrower(100, 100, "left", combat_sprites=pygame.sprite.Group(target))
    group = run(flame, 3.0)

    assert target.damage_taken > 0
    assert target.damage_taken % Flamethrower.DAMAGE == 0
    assert flame not in group


def test_flamethrower_beside_wall_still_fires():
    from pokemon_rpg.gameplay.combat.projectiles.flamethrower import Flamethrower

    wall = Wall((80, 105, 200, 32))
    flame = Flamethrower(100, 100, "left", collision_sprites=pygame.sprite.Group(wall))
    group = run(flame, 0.2)

    assert flame.particles
    assert flame in group


def test_flamethrower_blocked_by_wall_ahead():
    from pokemon_rpg.gameplay.combat.projectiles.flamethrower import Flamethrower

    wall = Wall((130, 0, 32, 200))
    target = DamageTarget((180, 100))
    flame = Flamethrower(
        100,
        100,
        "left",
        collision_sprites=pygame.sprite.Group(wall),
        combat_sprites=pygame.sprite.Group(target),
    )
    run(flame, 3.0)

    assert target.damage_taken == 0


def test_flamethrower_emission_is_frame_rate_independent():
    from pokemon_rpg.gameplay.combat.projectiles.flamethrower import Flamethrower

    counts = []
    for fps in (60, 144):
        flame = Flamethrower(100, 100, "left")
        bursts = 0
        original = flame._burst

        def counting_burst():
            nonlocal bursts
            bursts += 1
            original()

        flame._burst = counting_burst
        run(flame, 1.0, fps)
        counts.append(bursts)

    assert abs(counts[0] - counts[1]) <= 1


@pytest.mark.parametrize("move", ["bullet_seed", "razor_leaf"])
@pytest.mark.parametrize("fps", [60, 144])
def test_volley_fires_every_shot_while_caster_frozen(move, fps):
    from pokemon_rpg.gameplay.combat.moves import MOVE_CLASSES

    cls = MOVE_CLASSES[move]
    volley = cls(100, 100, "down")
    group = run(volley, cls.FREEZE_DURATION, fps)

    assert len(volley.shots) == cls.SHOT_COUNT
    assert not volley.active
    assert volley in group


def test_bullet_seed_hits_target_with_every_seed():
    from pokemon_rpg.gameplay.combat.projectiles.bullet_seed import BulletSeed, Seed

    target = DamageTarget((160, 100))
    target.rect.inflate_ip(40, 40)
    volley = BulletSeed(100, 100, "left", combat_sprites=pygame.sprite.Group(target))
    group = run(volley, 2.0)

    assert target.damage_taken == Seed.DAMAGE * BulletSeed.SHOT_COUNT
    assert volley not in group


def test_bullet_seed_blocked_by_wall_ahead():
    from pokemon_rpg.gameplay.combat.projectiles.bullet_seed import BulletSeed

    wall = Wall((130, 0, 32, 200))
    target = DamageTarget((180, 100))
    volley = BulletSeed(
        100,
        100,
        "left",
        collision_sprites=pygame.sprite.Group(wall),
        combat_sprites=pygame.sprite.Group(target),
    )
    group = run(volley, 2.0)

    assert target.damage_taken == 0
    assert volley not in group


def test_razor_leaf_slashes_target():
    from pokemon_rpg.gameplay.combat.projectiles.razor_leaf import Leaf, RazorLeaf

    target = DamageTarget((160, 100))
    target.rect.inflate_ip(40, 40)
    volley = RazorLeaf(100, 100, "left", combat_sprites=pygame.sprite.Group(target))
    group = pygame.sprite.Group(volley)

    slashed = False
    for _ in range(120):
        group.update(1 / 60)
        slashed |= any(leaf.slashes for leaf in volley.shots)

    assert slashed
    assert target.damage_taken == Leaf.DAMAGE * RazorLeaf.SHOT_COUNT
    assert volley not in group


def test_water_gun_splash_plays_after_impact():
    from pokemon_rpg.gameplay.combat.projectiles.water_gun import WaterGun

    wall = Wall((140, 90, 32, 32))
    gun = WaterGun(100, 100, "left", collision_sprites=pygame.sprite.Group(wall))
    group = run(gun, 0.1)

    assert not gun.active
    assert gun.splash and gun.rings
    assert gun in group

    run(gun, 1.0)
    assert gun not in group
