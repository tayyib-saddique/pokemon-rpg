import pygame
import math
import random
from projectiles.base import BaseProjectile

BG = (18, 22, 30)
C_WHITE = (255, 255, 220)
C_YELLOW = (255, 235, 30)
C_ORANGE = (255, 115, 0)
C_RED = (210, 20, 0)
C_DARK = (90, 12, 0)


def _blend(c, a):
    return tuple(int(c[i] * a + BG[i] * (1 - a)) for i in range(3))


def _diamond(cx, cy, w, h, angle):
    ca, sa = math.cos(angle), math.sin(angle)
    pts = [(w, 0), (0, h), (-w, 0), (0, -h)]
    return [(cx + ca * px - sa * py, cy + sa * px + ca * py) for px, py in pts]


class TrailShard:
    def __init__(self, x, y, angle, w, h, colour_t):
        self.x, self.y = float(x), float(y)
        self.angle = angle
        self.w, self.h = w, h
        self.colour_t = colour_t
        self.life = random.uniform(0.10, 0.22)
        self.max_life = self.life
        self.vx = random.uniform(-8, 8)
        self.vy = random.uniform(-8, 8)

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
        w = max(1, self.w * t)
        h = max(1, self.h * t)
        if self.colour_t > 0.7:
            outer, inner = C_ORANGE, C_YELLOW
        elif self.colour_t > 0.4:
            outer, inner = C_RED, C_ORANGE
        else:
            outer, inner = C_DARK, C_RED

        sx, sy = self.x - offset[0], self.y - offset[1]
        pts = _diamond(sx, sy, w, h, self.angle)
        pts_in = _diamond(sx, sy, w * 0.5, h * 0.5, self.angle)
        pygame.draw.polygon(surface, _blend(outer, 0.75 * t), pts)
        pygame.draw.polygon(surface, _blend(inner, t), pts_in)


class HeadShard:
    def __init__(self, angle, offset_perp, w, h, phase):
        self.angle = angle
        self.offset_perp = offset_perp
        self.w, self.h = w, h
        self.phase = phase
        self._t = phase

    def update(self, dt):
        self._t += dt

    def draw(self, surface, cx, cy, master_alpha=1.0):
        pulse = 1.0 + math.sin(self._t * 22 + self.phase) * 0.15
        perp_x = -math.sin(self.angle) * self.offset_perp
        perp_y = math.cos(self.angle) * self.offset_perp
        x = cx + perp_x
        y = cy + perp_y
        w = self.w * pulse
        h = self.h * pulse

        pts = _diamond(x, y, w, h, self.angle)
        pts_mid = _diamond(x, y, w * 0.6, h * 0.6, self.angle)
        pts_core = _diamond(x, y, w * 0.3, h * 0.3, self.angle)

        pygame.draw.polygon(surface, _blend(C_RED, 0.75 * master_alpha), pts)
        pygame.draw.polygon(surface, _blend(C_ORANGE, 0.90 * master_alpha), pts_mid)
        pygame.draw.polygon(surface, _blend(C_YELLOW, master_alpha), pts_core)
        if self.w > 10:
            pts_tip = _diamond(x, y, w * 0.15, h * 0.15, self.angle)
            pygame.draw.polygon(surface, _blend(C_WHITE, master_alpha), pts_tip)


class BurstShard:
    def __init__(self, x, y, dir_angle, index, total):
        angle = (
            dir_angle + math.tau / total * index + math.radians(random.uniform(-12, 12))
        )
        spd = random.uniform(100, 260)
        self.x, self.y = float(x), float(y)
        self.vx = math.cos(angle) * spd
        self.vy = math.sin(angle) * spd
        self.angle = angle
        self.w = random.uniform(8, 15)
        self.h = random.uniform(2, 5)
        self.life = random.uniform(0.15, 0.30)
        self.max_life = self.life

    @property
    def active(self):
        return self.life > 0

    def update(self, dt):
        self.vx *= 1 - 4.0 * dt
        self.vy *= 1 - 4.0 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    def draw(self, surface, offset=(0, 0)):
        t = self.life / self.max_life
        w = self.w * (0.25 + 0.75 * t)
        h = self.h * (0.25 + 0.75 * t)
        if t > 0.65:
            outer, inner = C_YELLOW, C_WHITE
        elif t > 0.35:
            outer, inner = C_ORANGE, C_YELLOW
        else:
            outer, inner = C_RED, C_ORANGE

        sx, sy = self.x - offset[0], self.y - offset[1]
        pts = _diamond(sx, sy, w, h, self.angle)
        pts_in = _diamond(sx, sy, w * 0.5, h * 0.5, self.angle)
        pygame.draw.polygon(surface, _blend(outer, 0.85 * t), pts)
        pygame.draw.polygon(surface, _blend(inner, t), pts_in)


class Ember(BaseProjectile):
    TRAIL_INTERVAL = 0.018
    BURST_COUNT = 16

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
            jx = self.pos.x + random.uniform(-3, 3)
            jy = self.pos.y + random.uniform(-3, 3)
            w = random.uniform(5, 9)
            h = random.uniform(2, 4)
            self.trail.append(TrailShard(jx, jy, self._dir, w, h, colour_t))

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
