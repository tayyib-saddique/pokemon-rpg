import math
import random

import pygame

from pokemon_rpg.gameplay.combat.projectiles.base import BaseProjectile
from pokemon_rpg.gameplay.combat.projectiles.volley import Volley

S_DARK = (64, 100, 32)
S_BODY = (156, 200, 72)
S_SHINE = (232, 248, 176)
S_STREAK = (196, 232, 120)
S_HUSK = (120, 92, 44)


def _oval_points(cx, cy, angle, length, width, steps=8):
    """Polygon for an oval whose long axis points along `angle`."""
    dx, dy = math.cos(angle), math.sin(angle)
    nx, ny = -dy, dx
    points = []
    for i in range(steps):
        t = math.tau * i / steps
        a = math.cos(t) * length
        b = math.sin(t) * width
        points.append((round(cx + dx * a + nx * b), round(cy + dy * a + ny * b)))
    return points


class StreakSpeck:
    """Speed streak left behind a seed: a pixel that shrinks in place."""

    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.size = random.randint(2, 3)
        self.life = random.uniform(0.06, 0.12)
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
        size = max(1, int(self.size * t + 0.5))
        px = int(self.x - offset[0]) - size // 2
        py = int(self.y - offset[1]) - size // 2
        pygame.draw.rect(surface, S_STREAK, (px, py, size, size))


class HuskFragment:
    """Seed casing that cracks off on impact and bounces back."""

    def __init__(self, x, y, dir_angle):
        # Kick back the way the seed came, fanned wide
        angle = dir_angle + math.pi + math.radians(random.uniform(-80, 80))
        spd = random.uniform(60, 160)
        self.x, self.y = float(x), float(y)
        self.vx = math.cos(angle) * spd
        self.vy = math.sin(angle) * spd
        self.size = random.randint(2, 3)
        self.color = random.choice((S_DARK, S_BODY, S_HUSK))
        self.life = random.uniform(0.15, 0.30)
        self.max_life = self.life

    @property
    def active(self):
        return self.life > 0

    def update(self, dt):
        self.vx *= 1 - 3.0 * dt
        self.vy += 220 * dt  # gravity so fragments drop
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    def draw(self, surface, offset=(0, 0)):
        if self.life <= 0:
            return
        px = int(self.x - offset[0]) - self.size // 2
        py = int(self.y - offset[1]) - self.size // 2
        pygame.draw.rect(surface, self.color, (px, py, self.size, self.size))


class Seed(BaseProjectile):
    """A single seed in a Bullet Seed volley."""

    DAMAGE = 4
    MAX_SCATTER = 4  # degrees of random heading per seed
    TRAIL_INTERVAL = 0.012
    POP_COUNT = 6
    FLASH_DURATION = 0.05

    def __init__(self, origin_x, origin_y, facing, spread=0, index=0, **kwargs):
        super().__init__(origin_x, origin_y, facing, speed=560, **kwargs)
        self.velocity.rotate_ip(
            spread + random.uniform(-self.MAX_SCATTER, self.MAX_SCATTER)
        )
        self._dir = math.atan2(self.velocity.y, self.velocity.x)

        # Small sideways jitter so consecutive seeds don't stack on one line
        side = random.uniform(-3, 3)
        self.pos += (
            pygame.math.Vector2(-math.sin(self._dir), math.cos(self._dir)) * side
        )

        self.streaks: list[StreakSpeck] = []
        self.husks: list[HuskFragment] = []
        self._trail_t = 0.0
        self._flash = 0.0

        self.rect = pygame.Rect(0, 0, 12, 12)
        self.rect.center = self.pos

    def on_deactivate(self):
        self._flash = self.FLASH_DURATION
        for _ in range(self.POP_COUNT):
            self.husks.append(HuskFragment(self.pos.x, self.pos.y, self._dir))

    def update_effects(self, dt):
        if self.active:
            self._trail_t += dt
            while self._trail_t >= self.TRAIL_INTERVAL:
                self._trail_t -= self.TRAIL_INTERVAL
                self.streaks.append(StreakSpeck(self.pos.x, self.pos.y))

        self._flash = max(0.0, self._flash - dt)
        for s in self.streaks:
            s.update(dt)
        for h in self.husks:
            h.update(dt)
        self.streaks = [s for s in self.streaks if s.active]
        self.husks = [h for h in self.husks if h.active]

    def has_effects(self):
        return bool(self.streaks or self.husks or self._flash > 0)

    def draw(self, surface, offset=(0, 0)):
        for s in self.streaks:
            s.draw(surface, offset)

        cx = self.pos.x - offset[0]
        cy = self.pos.y - offset[1]

        if self.active:
            # Motion streak behind the seed
            tail = (
                round(cx - math.cos(self._dir) * 12),
                round(cy - math.sin(self._dir) * 12),
            )
            pygame.draw.line(surface, S_STREAK, tail, (round(cx), round(cy)), 3)

            pygame.draw.polygon(surface, S_DARK, _oval_points(cx, cy, self._dir, 7, 5))
            pygame.draw.polygon(surface, S_BODY, _oval_points(cx, cy, self._dir, 5, 3))
            # Shine sits toward the front of the seed
            sx = round(cx + math.cos(self._dir) * 2)
            sy = round(cy + math.sin(self._dir) * 2) - 1
            pygame.draw.rect(surface, S_SHINE, (sx - 1, sy - 1, 2, 2))
        elif self._flash > 0:
            # One- or two-frame pop where the seed burst
            x, y = round(cx), round(cy)
            pygame.draw.rect(surface, S_SHINE, (x - 6, y - 1, 12, 2))
            pygame.draw.rect(surface, S_SHINE, (x - 1, y - 6, 2, 12))

        for h in self.husks:
            h.draw(surface, offset)


class BulletSeed(Volley):
    SHOT_CLASS = Seed
    SHOT_COUNT = 5
    SHOT_INTERVAL = 0.07
    # Caster holds the pose until the last seed leaves
    FREEZE_DURATION = SHOT_INTERVAL * (SHOT_COUNT - 1) + 0.06
