import math
import random

import pygame

from pokemon_rpg.gameplay.combat.projectiles.base import BaseProjectile
from pokemon_rpg.gameplay.combat.projectiles.volley import Volley

PIXEL = 3  # leaf pixels match the x3 scale of the Pokemon sprites

# Pixel-art palette: o outline, d dark, b body, l light, w shine
FRONT = {
    "o": (20, 40, 20),
    "d": (52, 116, 44),
    "b": (92, 176, 60),
    "l": (156, 220, 96),
    "w": (224, 248, 168),
}
# Underside, seen when the leaf tumbles over
BACK = {
    "o": (20, 40, 20),
    "d": (40, 92, 36),
    "b": (64, 136, 52),
    "l": (96, 168, 64),
    "w": (124, 192, 80),
}
SLASH = {"w": (255, 255, 255), "l": (200, 248, 160)}

# V-shaped leaf frames, front side: two straight blades meeting at a point,
# with a bright outer (cutting) edge, lit from the top-left. Each is drawn
# lying flat and tilted 45 degrees; the other six directions are lossless
# 90 degree turns of these, as a sprite game would do. Narrower stages are the
# leaf seen part-way through a tumble.
LEAF_ART = {
    ("face", "right"): [
        ".......ooo.......",
        "......olwlo......",
        ".....olbbblo.....",
        "....olbbbbblo....",
        "...olbbbdbbblo...",
        "..olbbbdodbbblo..",
        "..olbddo.oddblo..",
        ".olddoo...ooddlo.",
        "oldoo.......oodlo",
        "ooo...........ooo",
    ],
    ("narrow", "right"): [
        "........o........",
        ".....ooolooo.....",
        "....ollldlllo....",
        "..oolddoooddloo..",
        ".oldooo...ooodlo.",
        "oooo.........oooo",
    ],
    ("edge", "right"): [
        "...ooooooooooo...",
        "ooooooooooooooooo",
    ],
    ("face", "up_right"): [
        "..oooooooo...",
        ".owlllllllooo",
        "owbbbbbbbddoo",
        "olbbbddddoo..",
        "olbbdoooo....",
        "olbdo........",
        "olbdo........",
        "olbdo........",
        "olbdo........",
        "oldo.........",
        ".odo.........",
        ".oo..........",
        ".oo..........",
    ],
    ("narrow", "up_right"): [
        "..........oo",
        "......oooolo",
        "...ooolldoo.",
        "..olllddo...",
        "..olbdoo....",
        "..oldo......",
        ".oldo.......",
        ".oldo.......",
        ".odo........",
        ".oo.........",
        "olo.........",
        "oo..........",
    ],
    ("edge", "up_right"): [
        ".........oo",
        "........oo.",
        "......ooo..",
        ".....olo...",
        "....odo....",
        "...odo.....",
        "..olo......",
        "..oo.......",
        ".oo........",
        "oo.........",
        "o..........",
    ],
}

# One tumble end over end, a frame at a time: (stage, showing the underside)
TUMBLE = [
    ("face", False),
    ("narrow", False),
    ("edge", False),
    ("narrow", True),
    ("face", True),
    ("narrow", True),
    ("edge", True),
    ("narrow", False),
]
ANIM_FPS = 12  # sprite frames per second, like a hand-animated effect
SPIN_EVERY = 2  # animation frames per 45 degree turn
LEAF_REACH = 8 * PIXEL  # centre to tip, in world pixels

_sprite_cache = {}


def _turn_over(art, diagonal):
    """Flip the art across the leaf's long axis to show its underside.

    Light and dark swap so the underside stays lit from the top-left.
    """
    if diagonal:
        n = len(art)
        art = ["".join(art[n - 1 - x][n - 1 - y] for x in range(n)) for y in range(n)]
    else:
        art = art[::-1]
    swap = {"l": "d", "w": "d", "d": "l"}
    return ["".join(swap.get(c, c) for c in row) for row in art]


def _render(art, palette):
    sprite = pygame.Surface((len(art[0]), len(art)), pygame.SRCALPHA)
    for y, row in enumerate(art):
        for x, c in enumerate(row):
            if c != ".":
                sprite.set_at((x, y), palette[c])
    return pygame.transform.scale(
        sprite, (sprite.get_width() * PIXEL, sprite.get_height() * PIXEL)
    )


def _leaf_sprite(octant, stage, back):
    """Leaf pointing octant * 45 degrees anticlockwise from screen-right."""
    key = (octant, stage, back)
    if key not in _sprite_cache:
        diagonal = octant % 2 == 1
        art = LEAF_ART[(stage, "up_right" if diagonal else "right")]
        if back:
            art = _turn_over(art, diagonal)
        sprite = _render(art, BACK if back else FRONT)
        _sprite_cache[key] = pygame.transform.rotate(sprite, 90 * (octant // 2))
    return _sprite_cache[key]


def _slash_sprite(direction, reach):
    """A two-pixel-wide pixel streak along one of the four line directions."""
    key = (direction, reach)
    if key not in _sprite_cache:
        dx, dy = direction
        # Thicken by a pixel that shares an edge, so diagonals stay solid
        side = (1, 0) if dx and dy else (dy, dx)
        size = reach * 2 + 3
        art = [["."] * size for _ in range(size)]
        mid = size // 2
        for i in range(-reach, reach + 1):
            art[mid + i * dy][mid + i * dx] = "w"
            if abs(i) < reach:
                art[mid + i * dy + side[1]][mid + i * dx + side[0]] = "l"
        _sprite_cache[key] = _render(["".join(row) for row in art], SLASH)
    return _sprite_cache[key]


def _snapped(x, y, offset):
    """Screen point on the leaf pixel grid, so effects move in whole pixels."""
    return (
        round(x / PIXEL) * PIXEL - round(offset[0]),
        round(y / PIXEL) * PIXEL - round(offset[1]),
    )


class LeafFleck:
    """Chip of leaf shed in flight or on impact: one leaf pixel that fades."""

    def __init__(self, x, y, vx, vy, life_range=(0.10, 0.20), gravity=0):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = vx, vy
        self.gravity = gravity
        self.life = random.uniform(*life_range)
        self.max_life = self.life

    @property
    def active(self):
        return self.life > 0

    def update(self, dt):
        self.vx *= 1 - 3.0 * dt
        self.vy *= 1 - 3.0 * dt
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    def draw(self, surface, offset=(0, 0)):
        t = self.life / self.max_life
        if t <= 0:
            return
        # Steps down the palette instead of shrinking below a leaf pixel
        colour = FRONT["l"] if t > 0.66 else FRONT["b"] if t > 0.33 else FRONT["d"]
        x, y = _snapped(self.x, self.y, offset)
        pygame.draw.rect(surface, colour, (x, y, PIXEL, PIXEL))


class SlashMark:
    """Pixel cut that flashes across a target the leaf struck."""

    # Screen-space line directions a pixel slash can take
    DIRECTIONS = [(1, 0), (1, 1), (0, 1), (-1, 1)]

    def __init__(self, x, y, dir_angle):
        self.x, self.y = x, y
        # Cut across the line of travel, to the nearest 45 degrees
        angle = dir_angle + math.pi / 2 + math.radians(random.uniform(-25, 25))
        self.direction = self.DIRECTIONS[round(angle / (math.pi / 4)) % 4]
        self.life = 0.14
        self.max_life = self.life

    @property
    def active(self):
        return self.life > 0

    def update(self, dt):
        self.life -= dt

    def draw(self, surface, offset=(0, 0)):
        t = self.life / self.max_life
        if t <= 0:
            return
        # Two frames: full cut, then a shorter afterimage
        sprite = _slash_sprite(self.direction, 4 if t > 0.4 else 2)
        surface.blit(sprite, sprite.get_rect(center=_snapped(self.x, self.y, offset)))


class Leaf(BaseProjectile):
    """A single tumbling leaf in a Razor Leaf throw."""

    DAMAGE = 5
    WEAVE_DEG = 9  # peak heading swing either side of the throw line
    WEAVE_SPEED = 10  # radians/s
    TRAIL_INTERVAL = 0.05
    SHATTER_COUNT = 7

    def __init__(self, origin_x, origin_y, facing, spread=0, index=0, **kwargs):
        super().__init__(origin_x, origin_y, facing, speed=420, **kwargs)
        self.velocity.rotate_ip(spread)
        self._speed = self.velocity.length()
        self._base_dir = math.atan2(self.velocity.y, self.velocity.x)
        self._dir = self._base_dir

        # Alternate spin and weave so neighbouring leaves don't move in lockstep
        side = 1 if index % 2 == 0 else -1
        self._spin_dir = side
        self._weave_phase = 0.0 if side > 0 else math.pi
        self._octant = random.randrange(8)
        self._tumble = random.randrange(len(TUMBLE))
        self._frames = 0
        self._anim_t = 0.0
        self._t = 0.0

        self.flecks: list[LeafFleck] = []
        self.slashes: list[SlashMark] = []
        self._trail_t = 0.0

        self.rect = pygame.Rect(0, 0, 24, 24)
        self.rect.center = self.pos

    def _advance(self, dt):
        # Weave: swing the heading back and forth around the throw line
        self._t += dt
        weave = math.radians(self.WEAVE_DEG) * math.sin(
            self._t * self.WEAVE_SPEED + self._weave_phase
        )
        self._dir = self._base_dir + weave
        self.velocity.from_polar((self._speed, math.degrees(self._dir)))
        super()._advance(dt)

    def on_hit(self, target):
        super().on_hit(target)
        self.slashes.append(SlashMark(self.pos.x, self.pos.y, self._dir))

    def on_deactivate(self):
        for _ in range(self.SHATTER_COUNT):
            angle = random.uniform(0, math.tau)
            spd = random.uniform(50, 140)
            self.flecks.append(
                LeafFleck(
                    self.pos.x,
                    self.pos.y,
                    math.cos(angle) * spd,
                    math.sin(angle) * spd,
                    life_range=(0.18, 0.32),
                    gravity=160,
                )
            )

    def _animate(self, dt):
        self._anim_t += dt
        while self._anim_t >= 1 / ANIM_FPS:
            self._anim_t -= 1 / ANIM_FPS
            self._frames += 1
            self._tumble = (self._tumble + 1) % len(TUMBLE)
            if self._frames % SPIN_EVERY == 0:
                self._octant = (self._octant + self._spin_dir) % 8

    def update_effects(self, dt):
        if self.active:
            self._animate(dt)
            self._trail_t += dt
            while self._trail_t >= self.TRAIL_INTERVAL:
                self._trail_t -= self.TRAIL_INTERVAL
                # Shed from the leaf's tip as it spins
                angle = self._octant * math.pi / 4
                self.flecks.append(
                    LeafFleck(
                        self.pos.x + math.cos(angle) * LEAF_REACH,
                        self.pos.y - math.sin(angle) * LEAF_REACH,
                        random.uniform(-15, 15),
                        random.uniform(-15, 15),
                    )
                )

        for f in self.flecks:
            f.update(dt)
        for s in self.slashes:
            s.update(dt)
        self.flecks = [f for f in self.flecks if f.active]
        self.slashes = [s for s in self.slashes if s.active]

    def has_effects(self):
        return bool(self.flecks or self.slashes)

    def draw(self, surface, offset=(0, 0)):
        for f in self.flecks:
            f.draw(surface, offset)

        if self.active:
            stage, back = TUMBLE[self._tumble]
            sprite = _leaf_sprite(self._octant, stage, back)
            centre = _snapped(self.pos.x, self.pos.y, offset)
            surface.blit(sprite, sprite.get_rect(center=centre))

        for s in self.slashes:
            s.draw(surface, offset)


class RazorLeaf(Volley):
    SHOT_CLASS = Leaf
    SHOT_COUNT = 3
    SHOT_INTERVAL = 0.08
    SPREAD = (0, -10, 10)  # thrown in a fan
    FREEZE_DURATION = SHOT_INTERVAL * (SHOT_COUNT - 1) + 0.08
