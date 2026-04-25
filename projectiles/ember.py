import pygame
import math
import random
from projectiles.base import BaseProjectile

C_WHITE = (255, 255, 220)
C_YELLOW = (255, 235, 30)
C_ORANGE = (255, 115, 0)
C_RED = (210, 20, 0)
C_DARK = (90, 12, 0)

GRAVITY = 35  # pixels/s^2 — slight downward arc


def _pixel_cross(surface, cx, cy, w, h, color):
    """Pixel-art cross/plus shape: two axis-aligned rects."""
    pw, ph = max(1, int(w)), max(1, int(h))
    pygame.draw.rect(surface, color, (cx - pw // 2, cy - ph // 2, pw, ph))
    pygame.draw.rect(surface, color, (cx - ph // 2, cy - pw // 2, ph, pw))


class TrailShard:
    def __init__(self, x, y, w, h, colour_t):
        self.x, self.y = float(x), float(y)
        self.colour_t = colour_t
        self.size = max(2, int((w + h) / 2))
        self.life = random.uniform(0.10, 0.22)
        self.max_life = self.life
        self.vx = random.uniform(-6, 6)
        self.vy = random.uniform(-6, 6)

    @property
    def active(self):
        return self.life > 0

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    def draw(self, surface, offset=(0, 0)):
        t = self.life / self.max_life
        if t <= 0:
            return
        size = max(1, int(self.size * t))
        if self.colour_t > 0.7:
            color = C_YELLOW
        elif self.colour_t > 0.4:
            color = C_ORANGE
        else:
            color = C_RED
        px = int(self.x - offset[0]) - size // 2
        py = int(self.y - offset[1]) - size // 2
        pygame.draw.rect(surface, color, (px, py, size, size))


class HeadShard:
    def __init__(self, angle, offset_perp, w, h, phase):
        self.angle = angle
        self.offset_perp = offset_perp
        self.w, self.h = w, h
        self.phase = phase
        self._t = phase

    def update(self, dt):
        self._t += dt

    def draw(self, surface, cx, cy):
        # Stepped pulse: toggles between two sizes every ~6 frames — no smooth sin
        pulse = 1.1 if int(self._t * 10) % 2 == 0 else 1.0
        perp_x = int(-math.sin(self.angle) * self.offset_perp)
        perp_y = int(math.cos(self.angle) * self.offset_perp)
        x = cx + perp_x
        y = cy + perp_y
        w = max(2, int(self.w * pulse))
        h = max(2, int(self.h * pulse))

        # Outer cross (red)
        _pixel_cross(surface, x, y, w, h, C_RED)
        # Inner cross (orange)
        _pixel_cross(surface, x, y, max(1, w // 2), max(1, h // 2), C_ORANGE)
        # Core pixel (yellow)
        if w > 6:
            pygame.draw.rect(surface, C_YELLOW, (x - 1, y - 1, 2, 2))
        # Hot centre (white)
        if w > 10:
            pygame.draw.rect(surface, C_WHITE, (x, y, 1, 1))


class BurstShard:
    def __init__(self, x, y, dir_angle, index, total):
        angle = (
            dir_angle + math.tau / total * index + math.radians(random.uniform(-12, 12))
        )
        spd = random.uniform(80, 220)
        self.x, self.y = float(x), float(y)
        self.vx = math.cos(angle) * spd
        self.vy = math.sin(angle) * spd
        self.size = random.randint(2, 4)
        self.life = random.uniform(0.15, 0.30)
        self.max_life = self.life

    @property
    def active(self):
        return self.life > 0

    def update(self, dt):
        self.vx *= 1 - 4.0 * dt
        self.vy *= 1 - 4.0 * dt
        self.vy += 30 * dt  # light gravity so shards arc downward
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    def draw(self, surface, offset=(0, 0)):
        t = self.life / self.max_life
        if t <= 0:
            return
        size = max(1, int(self.size * t))
        if t > 0.65:
            color = C_YELLOW
        elif t > 0.35:
            color = C_ORANGE
        else:
            color = C_RED
        px = int(self.x - offset[0]) - size // 2
        py = int(self.y - offset[1]) - size // 2
        pygame.draw.rect(surface, color, (px, py, size, size))


class Ember(BaseProjectile):
    TRAIL_INTERVAL = 0.022
    BURST_COUNT = 16
    FREEZE_DURATION = 0.08

    HEAD_SHARDS = [
        (0, 13, 5, 0.0),
        (4, 9, 4, 1.2),
        (-4, 9, 4, 2.4),
        (2, 6, 3, 0.8),
        (-2, 6, 3, 3.2),
    ]

    def __init__(self, origin_x, origin_y, facing, **kwargs):
        super().__init__(origin_x, origin_y, facing, speed=460, **kwargs)
        self._dir = math.atan2(self.velocity.y, self.velocity.x)
        self._speed = self.velocity.length()

        self.head_shards = [
            HeadShard(self._dir, op, w, h, ph) for op, w, h, ph in self.HEAD_SHARDS
        ]
        self.trail: list[TrailShard] = []
        self.burst: list[BurstShard] = []
        self._trail_t = 0.0
        self._exploded = False
        self._age = 0.0

        self.rect = pygame.Rect(0, 0, 30, 30)
        self.rect.center = self.pos

    def impact(self):
        if not self._exploded:
            self._exploded = True
            self.active = False
            for i in range(self.BURST_COUNT):
                self.burst.append(
                    BurstShard(self.pos.x, self.pos.y, self._dir, i, self.BURST_COUNT)
                )

    def update(self, dt, *args, **kwargs):
        if not self._exploded:
            # Pixel physics: gravity gives ember a falling arc
            self.velocity.y += GRAVITY * dt

            super().update(dt)
            self.rect.center = self.pos

            self._age += dt
            for hs in self.head_shards:
                hs.update(dt)
            self._trail_t += dt
            if self._trail_t >= self.TRAIL_INTERVAL:
                self._trail_t = 0.0
                self._deposit_trail()
            if not self.active:
                self.impact()

        for ts in self.trail:
            ts.update(dt)
        for bs in self.burst:
            bs.update(dt)
        self.trail = [ts for ts in self.trail if ts.active]
        self.burst = [bs for bs in self.burst if bs.active]

    def _deposit_trail(self):
        for _ in range(random.randint(2, 3)):
            colour_t = max(0.0, 1.0 - self._age * 3.5)
            jx = self.pos.x + random.randint(-3, 3)
            jy = self.pos.y + random.randint(-3, 3)
            w = random.uniform(4, 8)
            h = random.uniform(2, 4)
            self.trail.append(TrailShard(jx, jy, w, h, colour_t))

    def draw(self, surface, offset=(0, 0)):
        for ts in self.trail:
            ts.draw(surface, offset)

        if not self._exploded:
            cx = int(self.pos.x - offset[0])
            cy = int(self.pos.y - offset[1])
            for hs in self.head_shards:
                hs.draw(surface, cx, cy)

        for bs in self.burst:
            bs.draw(surface, offset)
