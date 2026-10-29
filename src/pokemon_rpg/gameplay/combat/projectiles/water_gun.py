import math
import random

import pygame

from pokemon_rpg.gameplay.combat.projectiles.base import BaseProjectile

W_DEEP = (32, 88, 200)
W_MID = (64, 152, 240)
W_LIGHT = (150, 210, 255)
W_WHITE = (235, 248, 255)

GRAVITY = 20  # pixels/s^2 — pressurised jet, barely droops


class Droplet:
    """Water droplet: shed as spray behind the jet, or thrown out by a splash."""

    def __init__(self, x, y, vx, vy, life_range, gravity):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = vx, vy
        self.gravity = gravity
        self.size = random.randint(2, 4)
        self.color = random.choice((W_MID, W_LIGHT, W_LIGHT, W_WHITE))
        self.life = random.uniform(*life_range)
        self.max_life = self.life

    @property
    def active(self):
        return self.life > 0

    def update(self, dt):
        self.vx *= 1 - 2.0 * dt
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    def draw(self, surface, offset=(0, 0)):
        t = self.life / self.max_life
        if t <= 0:
            return
        size = max(1, int(self.size * t + 0.5))
        px = int(self.x - offset[0]) - size // 2
        py = int(self.y - offset[1]) - size // 2
        pygame.draw.rect(surface, self.color, (px, py, size, size))


class SplashRing:
    """Flat ring that spreads out where the jet landed."""

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.life = 0.22
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
        # Stepped growth keeps the ring crisp rather than smoothly scaling
        r = 6 + 4 * int((1 - t) * 4)
        rect = pygame.Rect(0, 0, r * 2, r)
        rect.center = (int(self.x - offset[0]), int(self.y - offset[1]))
        pygame.draw.ellipse(surface, W_LIGHT if t > 0.4 else W_MID, rect, 2)


class WaterGun(BaseProjectile):
    TRAIL_INTERVAL = 0.016
    SPLASH_COUNT = 14
    FREEZE_DURATION = 0.10

    # Comet body: (distance behind the head, radius), head first
    BODY = ((0, 6), (4, 5), (8, 4), (12, 3), (15, 2))

    def __init__(self, origin_x, origin_y, facing, **kwargs):
        super().__init__(origin_x, origin_y, facing, speed=520, **kwargs)

        self.spray: list[Droplet] = []
        self.splash: list[Droplet] = []
        self.rings: list[SplashRing] = []
        self._trail_t = 0.0
        self._t = 0.0

        self.rect = pygame.Rect(0, 0, 14, 14)
        self.rect.center = self.pos

    def _advance(self, dt):
        self.velocity.y += GRAVITY * dt
        super()._advance(dt)

    def on_deactivate(self):
        back = math.atan2(-self.velocity.y, -self.velocity.x)
        for _ in range(self.SPLASH_COUNT):
            angle = back + math.radians(random.uniform(-75, 75))
            spd = random.uniform(60, 200)
            self.splash.append(
                Droplet(
                    self.pos.x,
                    self.pos.y,
                    math.cos(angle) * spd,
                    math.sin(angle) * spd - 60,  # thrown up a little before falling
                    life_range=(0.20, 0.40),
                    gravity=380,
                )
            )
        self.rings.append(SplashRing(self.pos.x, self.pos.y))

    def _shed_spray(self):
        d = self.velocity.normalize()
        for _ in range(2):
            side = random.uniform(-14, 14)
            self.spray.append(
                Droplet(
                    self.pos.x - d.x * 8 + random.randint(-2, 2),
                    self.pos.y - d.y * 8 + random.randint(-2, 2),
                    # Lags behind the head with a little sideways mist
                    self.velocity.x * 0.25 - d.y * side,
                    self.velocity.y * 0.25 + d.x * side,
                    life_range=(0.12, 0.26),
                    gravity=220,
                )
            )

    def update_effects(self, dt):
        if self.active:
            self._t += dt
            self._trail_t += dt
            while self._trail_t >= self.TRAIL_INTERVAL:
                self._trail_t -= self.TRAIL_INTERVAL
                self._shed_spray()

        for group in (self.spray, self.splash, self.rings):
            for p in group:
                p.update(dt)
        self.spray = [p for p in self.spray if p.active]
        self.splash = [p for p in self.splash if p.active]
        self.rings = [r for r in self.rings if r.active]

    def has_effects(self):
        return bool(self.spray or self.splash or self.rings)

    def draw(self, surface, offset=(0, 0)):
        for p in self.spray:
            p.draw(surface, offset)
        for r in self.rings:
            r.draw(surface, offset)

        if self.active:
            d = self.velocity.normalize()
            hx = self.pos.x - offset[0]
            hy = self.pos.y - offset[1]
            # Stepped pulse like Ember's head, so the jet looks pressurised
            pulse = 1 if int(self._t * 12) % 2 == 0 else 0
            segments = [
                ((round(hx - d.x * back), round(hy - d.y * back)), r + pulse)
                for back, r in self.BODY
            ]
            # Draw tail-to-head so the head sits on top
            for centre, r in reversed(segments):
                pygame.draw.circle(surface, W_DEEP, centre, r + 1)
            for centre, r in reversed(segments):
                pygame.draw.circle(surface, W_MID, centre, r)
            for centre, r in segments[:3]:
                pygame.draw.circle(surface, W_LIGHT, centre, max(1, r // 2))
            # Glint on the leading edge
            (gx, gy), _ = segments[0]
            gx += round(d.x * 2)
            gy += round(d.y * 2) - 2
            pygame.draw.rect(surface, W_WHITE, (gx - 1, gy - 1, 2, 2))

        for p in self.splash:
            p.draw(surface, offset)
