"""Stress tests run against every registered move.

Each move is pushed through hostile conditions: irregular frame times, walls
on every side, crowds of targets that die mid-attack, map corners, extreme
camera offsets and mass spawns. Deselect with `pytest -m "not stress"`.
"""

import math
import random
import time

import pygame
import pytest

from pokemon_rpg.gameplay.combat.moves import MOVE_CLASSES
from pokemon_rpg.gameplay.combat.projectiles.base import (
    FACING_VELOCITY,
    BaseProjectile,
)
from pokemon_rpg.gameplay.combat.projectiles.flamethrower import Flamethrower
from pokemon_rpg.gameplay.combat.projectiles.volley import Volley

pytestmark = pytest.mark.stress

MOVES = sorted(MOVE_CLASSES)
FACINGS = list(FACING_VELOCITY)
MAP_SIZE = (1440, 1440)
TILE = 48  # collision tiles are 16px scaled x3
LIFETIME_LIMIT = 5.0  # seconds any move may stay in its sprite groups

# Frame hitches: the game loop passes clock.tick() through uncapped
SPIKY_DTS = [1 / 60, 1 / 240, 0.0, 1 / 60, 0.05, 1 / 144, 1 / 30, 0.1, 1 / 60]


@pytest.fixture(autouse=True)
def seeded_random():
    random.seed(1234)


class Wall(pygame.sprite.Sprite):
    def __init__(self, rect):
        super().__init__()
        self.rect = pygame.Rect(rect)


class Target(pygame.sprite.Sprite):
    def __init__(self, centre, hp=None, size=24):
        super().__init__()
        self.rect = pygame.Rect(0, 0, size, size)
        self.rect.center = (round(centre[0]), round(centre[1]))
        self.hp = hp
        self.hits = []
        self.hits_after_death = 0

    def take_damage(self, amount, source=None):
        if not self.alive() and self.hp is not None:
            self.hits_after_death += 1
        self.hits.append(amount)
        if self.hp is not None:
            self.hp -= amount
            if self.hp <= 0:
                self.kill()


def ahead(origin, facing, distance):
    vx, vy = FACING_VELOCITY[facing]
    length = math.hypot(vx, vy)
    return origin[0] + vx / length * distance, origin[1] + vy / length * distance


def fire(move, origin, facing, walls=(), targets=()):
    return MOVE_CLASSES[move](
        origin[0],
        origin[1],
        facing,
        map_size=MAP_SIZE,
        collision_sprites=pygame.sprite.Group(*walls),
        combat_sprites=pygame.sprite.Group(*targets),
    )


def run_until_gone(projectile, dts=(1 / 60,), limit=LIFETIME_LIMIT, surface=None):
    """Update (and draw) until the projectile leaves its group. Returns seconds."""
    group = pygame.sprite.Group(projectile)
    elapsed, frame = 0.0, 0
    offset = (projectile.pos.x - 160, projectile.pos.y - 120)
    while projectile in group and elapsed <= limit:
        dt = dts[frame % len(dts)]
        group.update(dt)
        if surface is not None:
            projectile.draw(surface, offset)
        elapsed += dt
        frame += 1
    assert projectile not in group, f"still alive after {limit}s"
    return elapsed


def time_until_inactive(projectile, dt, limit=LIFETIME_LIMIT):
    elapsed = 0.0
    while projectile.active and elapsed <= limit:
        projectile.update(dt)
        elapsed += dt
    assert not projectile.active
    return elapsed


def boxed_in(origin, half=60):
    """Walls one tile thick enclosing `origin` on every side."""
    ox, oy = origin
    outer = half + TILE
    return [
        Wall((ox - outer, oy - outer, outer * 2, TILE)),
        Wall((ox - outer, oy + half, outer * 2, TILE)),
        Wall((ox - outer, oy - half, TILE, half * 2)),
        Wall((ox + half, oy - half, TILE, half * 2)),
    ]


def effect_count(projectile):
    """Live particles/sub-shots, counted through a volley's shots."""
    count = 0
    for name, value in vars(projectile).items():
        if name.startswith("_") or name.endswith("_sprites"):
            continue
        if isinstance(value, list):
            count += sum(
                effect_count(v) if isinstance(v, BaseProjectile) else 1 for v in value
            )
    return count


def max_hits(move):
    """Most separate damage events a single cast can deal in total."""
    cls = MOVE_CLASSES[move]
    if issubclass(cls, Volley):
        return cls.SHOT_COUNT
    return 1


@pytest.fixture
def surface():
    return pygame.Surface((320, 240))


@pytest.mark.parametrize("facing", FACINGS)
@pytest.mark.parametrize("move", MOVES)
def test_move_finishes_in_open_field(move, facing, surface):
    projectile = fire(move, (720, 720), facing)

    run_until_gone(projectile, surface=surface)

    assert not projectile.active
    assert not projectile.has_effects()


@pytest.mark.parametrize("move", MOVES)
def test_move_survives_frame_spikes(move, surface):
    origin = (720, 720)
    walls = [Wall((900, 600, TILE, 240))]
    targets = [Target(ahead(origin, facing, 90)) for facing in FACINGS]
    projectiles = [fire(move, origin, f, walls, targets) for f in FACINGS]

    for projectile in projectiles:
        run_until_gone(projectile, dts=SPIKY_DTS, surface=surface)


@pytest.mark.parametrize("move", MOVES)
def test_move_tolerates_zero_dt(move, surface):
    projectile = fire(move, (720, 720), "down")
    group = pygame.sprite.Group(projectile)

    for _ in range(300):
        group.update(0.0)
        projectile.draw(surface)

    assert projectile in group
    run_until_gone(projectile)


def targets_round_box(origin):
    # Just beyond the box walls in every direction, but within every move's
    # reach (Flamethrower's flame tops out around 180px)
    return [Target(ahead(origin, f, 150), size=40) for f in FACINGS]


@pytest.mark.parametrize("fps", [60, 20])
@pytest.mark.parametrize("facing", FACINGS)
@pytest.mark.parametrize("move", MOVES)
def test_walls_contain_move(move, facing, fps):
    origin = (720, 720)

    # Control: with the walls gone the move does reach the targets
    open_targets = targets_round_box(origin)
    run_until_gone(fire(move, origin, facing, targets=open_targets), dts=(1 / fps,))
    assert any(t.hits for t in open_targets)

    targets = targets_round_box(origin)
    projectile = fire(move, origin, facing, boxed_in(origin), targets)
    run_until_gone(projectile, dts=(1 / fps,))

    assert all(not t.hits for t in targets)


@pytest.mark.parametrize("move", MOVES)
def test_move_fired_from_inside_wall_finishes(move):
    # Caster's mouth clipped deep into a wall block
    walls = [Wall((600, 600, TILE * 5, TILE * 5))]
    for facing in FACINGS:
        run_until_gone(fire(move, (720, 720), facing, walls))


@pytest.mark.parametrize("facing", FACINGS)
@pytest.mark.parametrize("move", MOVES)
def test_targets_dying_mid_attack(move, facing):
    origin = (720, 720)
    # A dense crowd of one-hit targets in the line of fire
    targets = [
        Target(ahead(origin, facing, d), hp=1, size=20) for d in range(40, 200, 24)
    ]
    projectile = fire(move, origin, facing, targets=targets)

    run_until_gone(projectile)

    assert any(not t.alive() for t in targets)
    assert all(t.hits_after_death == 0 for t in targets)


@pytest.mark.parametrize("move", MOVES)
def test_damage_per_cast_is_bounded(move):
    origin = (720, 720)
    # 5x5 grid of sturdy targets directly ahead
    targets = [
        Target(ahead((origin[0] + dy, origin[1] + dx), "left", 60 + dx), size=28)
        for dx in range(0, 150, 30)
        for dy in range(-60, 61, 30)
    ]
    projectile = fire(move, origin, "left", targets=targets)

    elapsed = run_until_gone(projectile)

    hits = [amount for t in targets for amount in t.hits]
    assert hits, "move never connected"
    cls = MOVE_CLASSES[move]
    if cls is Flamethrower:
        # Each target ticks at most once per DAMAGE_TICK
        per_target = math.ceil(elapsed / cls.DAMAGE_TICK) + 1
        assert all(len(t.hits) <= per_target for t in targets)
    else:
        assert len(hits) <= max_hits(move)


@pytest.mark.parametrize(
    ("corner", "facings"),
    [
        ((2, 2), ["right", "up", "up_right"]),
        ((1438, 2), ["left", "up", "up_left"]),
        ((2, 1438), ["right", "down", "down_right"]),
        ((1438, 1438), ["left", "down", "down_left"]),
    ],
)
@pytest.mark.parametrize("move", MOVES)
def test_move_fired_off_map_corner(move, corner, facings):
    for facing in facings:
        projectile = fire(move, corner, facing)
        run_until_gone(projectile)
        if not isinstance(projectile, (Volley, Flamethrower)):
            # Moving projectiles should leave the map almost immediately
            fresh = fire(move, corner, facing)
            assert time_until_inactive(fresh, 1 / 60) < 0.1


@pytest.mark.parametrize("move", MOVES)
def test_move_timing_is_frame_rate_independent(move):
    times = {}
    for fps in (30, 144):
        random.seed(99)
        times[fps] = time_until_inactive(fire(move, (720, 720), "down"), 1 / fps)

    assert abs(times[30] - times[144]) <= 2 / 30


def lead_body(projectile):
    """The thing that actually flies: a volley's first shot, else the projectile."""
    return projectile.shots[0] if isinstance(projectile, Volley) else projectile


@pytest.mark.parametrize("facing", ["down", "up_left"])
@pytest.mark.parametrize("move", MOVES)
def test_move_path_is_frame_rate_independent(move, facing):
    # 1/6 s and 1/3 s land exactly on frame boundaries at both 30 and 144 fps
    samples = {}
    for fps in (30, 144):
        random.seed(99)
        projectile = fire(move, (720, 720), facing)
        positions = []
        for frame in range(1, fps // 3 + 1):
            projectile.update(1 / fps)
            if frame % (fps // 6) == 0:
                positions.append(pygame.math.Vector2(lead_body(projectile).pos))
        samples[fps] = positions

    for slow, fast in zip(samples[30], samples[144]):
        assert slow.distance_to(fast) <= 2


@pytest.mark.parametrize("facing", FACINGS)
@pytest.mark.parametrize("move", MOVES)
def test_move_stays_within_its_range(move, facing):
    projectile = fire(move, (720, 720), facing)
    group = pygame.sprite.Group(projectile)
    dt = 1 / 60

    while projectile in group:
        group.update(dt)
        if isinstance(projectile, Flamethrower):
            # Walls are only collected within _REACH, so flame must not pass it
            nozzle = pygame.math.Vector2(projectile._nx, projectile._ny)
            for p in projectile.particles:
                assert nozzle.distance_to((p.x, p.y)) <= Flamethrower._REACH
            continue
        bodies = projectile.shots if isinstance(projectile, Volley) else [projectile]
        for body in bodies:
            # One frame of travel past the limit before the check trips
            step = body.velocity.length() * dt
            assert body._origin.distance_to(body.pos) <= body.max_range + step + 1


@pytest.mark.parametrize("move", MOVES)
def test_move_draws_at_extreme_camera_offsets(move, surface):
    projectile = fire(move, (720, 720), "down_left")
    group = pygame.sprite.Group(projectile)
    offsets = [(0, 0), (-1e5, 1e5), (1e6, -1e6), (720.5, 720.5), (-720, -720)]

    frame = 0
    while projectile in group and frame < 600:
        group.update(1 / 60)
        projectile.draw(surface, offsets[frame % len(offsets)])
        frame += 1

    assert projectile not in group


def test_mass_spawn_of_every_move_stays_within_frame_budget(surface):
    """Every move cast 20 times at once among walls and targets."""
    rng = random.Random(7)
    walls = [
        Wall((rng.randrange(0, 1400), rng.randrange(0, 1400), TILE, TILE))
        for _ in range(60)
    ]
    targets = [
        Target((rng.randrange(0, 1440), rng.randrange(0, 1440)), hp=40)
        for _ in range(40)
    ]
    wall_group = pygame.sprite.Group(*walls)
    target_group = pygame.sprite.Group(*targets)
    group = pygame.sprite.Group()
    for move in MOVES:
        for _ in range(20):
            group.add(
                MOVE_CLASSES[move](
                    rng.randrange(100, 1340),
                    rng.randrange(100, 1340),
                    rng.choice(FACINGS),
                    map_size=MAP_SIZE,
                    collision_sprites=wall_group,
                    combat_sprites=target_group,
                )
            )

    frame_ms = []
    while group and len(frame_ms) < int(LIFETIME_LIMIT * 60):
        start = time.perf_counter()
        group.update(1 / 60)
        for projectile in group:
            projectile.draw(surface, (0, 0))
        frame_ms.append((time.perf_counter() - start) * 1000)

    assert not group, "projectiles outlived the lifetime limit"
    # Loose guard against pathological slowdowns only: 120 simultaneous casts
    # is far beyond normal play, and wall-clock time varies with machine load.
    median = sorted(frame_ms)[len(frame_ms) // 2]
    assert median < 100, f"median frame took {median:.1f} ms"


@pytest.mark.parametrize("move", MOVES)
def test_effects_stay_bounded_across_frame_rates(move):
    # Emission is time-based, so a fast machine must not pile up more effects
    peaks = {}
    for fps in (30, 240):
        random.seed(5)
        projectile = fire(move, (720, 720), "down")
        group = pygame.sprite.Group(projectile)
        peak = 0
        while projectile in group:
            group.update(1 / fps)
            peak = max(peak, effect_count(projectile))
        peaks[fps] = peak

    assert peaks[240] <= peaks[30] * 1.5 + 10
    assert max(peaks.values()) <= 400
