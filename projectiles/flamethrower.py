import pygame
import math
import random
from projectiles.base import BaseProjectile
from settings import WIDTH, HEIGHT

BG            = (18, 22, 30)
NOZZLE_OFFSET = 22

C_WHITE  = (255, 255, 220)
C_YELLOW = (255, 235,  30)
C_ORANGE = (255, 115,   0)
C_RED    = (210,  20,   0)
C_DARK   = ( 80,  10,   0)


def _blend(c, a):
    return (
        int(c[0] * a + BG[0] * (1 - a)),
        int(c[1] * a + BG[1] * (1 - a)),
        int(c[2] * a + BG[2] * (1 - a)),
    )


def _rotated_diamond(cx, cy, w, h, angle):
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    pts = [( 0, -h), ( w,  0), ( 0,  h), (-w,  0)]
    return [
        (cx + cos_a * px - sin_a * py,
         cy + sin_a * px + cos_a * py)
        for px, py in pts
    ]


class JetParticle:
    BASE_H = 4

    def __init__(self, nx, ny, dir_angle, speed):
        spread     = math.radians(random.uniform(-6, 6))
        self.angle = dir_angle + spread
        spd        = speed * random.uniform(0.85, 1.10)

        self.x  = float(nx)
        self.y  = float(ny)
        self.vx = math.cos(self.angle) * spd
        self.vy = math.sin(self.angle) * spd

        self.life     = random.uniform(0.28, 0.56)
        self.max_life = self.life
        self.w        = random.uniform(7, 12)
        self.h        = self.BASE_H
        self._start_x = float(nx)
        self._start_y = float(ny)


    def update(self, dt):
        drag    = 1.0 - 0.35 * dt
        self.vx *= drag
        self.vy *= drag
        self.x  += self.vx * dt
        self.y  += self.vy * dt
        self.life -= dt
        dist   = math.hypot(self.x - self._start_x, self.y - self._start_y)
        self.h = self.BASE_H + dist * 0.08

    @property
    def active(self):
        return self.life > 0

    def draw(self, surface, offset=(0, 0)):
        t = self.life / self.max_life
        if t <= 0:
            return

        a = min(1.0, t / 0.20) if t < 0.20 else 1.0

        if   t > 0.75: inner, outer = C_WHITE,  C_YELLOW
        elif t > 0.50: inner, outer = C_YELLOW, C_ORANGE
        elif t > 0.25: inner, outer = C_ORANGE, C_RED
        else:          inner, outer = C_RED,    C_DARK

        # Apply camera offset
        sx = self.x - offset[0]
        sy = self.y - offset[1]
        w  = max(2, int(self.w * (0.5 + 0.5 * t)))
        h  = max(2, int(self.h))

        pts_outer = _rotated_diamond(sx, sy, w, h, self.angle)
        pygame.draw.polygon(surface, _blend(outer, 0.85 * a), pts_outer)

        pts_inner = _rotated_diamond(sx, sy, max(1, int(w * 0.55)), max(1, int(h * 0.50)), self.angle)
        pygame.draw.polygon(surface, _blend(inner, 1.00 * a), pts_inner)


class EdgeSpark:
    def __init__(self, x, y, dir_angle, beam_speed):
        side  = random.choice((-1, 1))
        kick  = dir_angle + math.pi / 2 * side + math.radians(random.uniform(-20, 20))
        spd   = beam_speed * random.uniform(0.15, 0.40)
        self.x  = float(x)
        self.y  = float(y)
        self.vx = math.cos(kick) * spd + math.cos(dir_angle) * beam_speed * 0.35
        self.vy = math.sin(kick) * spd + math.sin(dir_angle) * beam_speed * 0.35
        self.life     = random.uniform(0.10, 0.22)
        self.max_life = self.life

    def update(self, dt):
        self.vy  += 60 * dt
        self.vx  *= (1 - 2.0 * dt)
        self.x   += self.vx * dt
        self.y   += self.vy * dt
        self.life -= dt

    @property
    def active(self):
        return self.life > 0

    def draw(self, surface, offset=(0, 0)):
        t   = self.life / self.max_life
        col = C_YELLOW if t > 0.5 else C_ORANGE
        r   = 1 if t < 0.4 else 2
        pygame.draw.circle(surface, _blend(col, t * 0.9),
                           (int(self.x - offset[0]), int(self.y - offset[1])), r)


class NozzleFlash:
    def __init__(self, nx, ny):
        self.x, self.y = nx, ny
        self.life      = 0.10
        self.max_life  = 0.10

    def update(self, dt):
        self.life -= dt

    @property
    def active(self):
        return self.life > 0

    def draw(self, surface, offset=(0, 0)):
        t  = self.life / self.max_life
        r  = int(5 + (1 - t) * 18)
        sx = int(self.x - offset[0])
        sy = int(self.y - offset[1])
        if r > 1:
            pygame.draw.circle(surface, _blend(C_WHITE,  t * 0.95), (sx, sy), r, 2)
            if r > 5:
                pygame.draw.circle(surface, _blend(C_YELLOW, t * 0.70), (sx, sy), r - 4, 1)


class Flamethrower(BaseProjectile):
    BURST_INTERVAL      = 0.013
    PARTICLES_PER_BURST = 3
    SPARK_CHANCE        = 0.50

    def __init__(self, origin_x, origin_y, facing, duration=1.2):
        super().__init__(origin_x, origin_y, facing, speed=360)

        self._dir   = math.atan2(self.velocity.y, self.velocity.x)
        self._speed = self.velocity.length()

        self._nx = float(origin_x) + math.cos(self._dir) * NOZZLE_OFFSET
        self._ny = float(origin_y) + math.sin(self._dir) * NOZZLE_OFFSET

        self._duration = duration
        self._emit_t   = 0.0
        self._timer    = 0.0

        self.particles: list[JetParticle] = []
        self.sparks:    list[EdgeSpark]   = []
        self._flash:    list[NozzleFlash] = [NozzleFlash(self._nx, self._ny)]

    def _burst(self):
        for _ in range(self.PARTICLES_PER_BURST):
            self.particles.append(JetParticle(self._nx, self._ny, self._dir, self._speed))
        if random.random() < self.SPARK_CHANCE:
            self.sparks.append(EdgeSpark(self._nx, self._ny, self._dir, self._speed))

    def update(self, dt):
        self._timer += dt

        if self._emit_t < self._duration:
            self._emit_t += dt
            if self._timer >= self.BURST_INTERVAL:
                self._timer = 0.0
                self._burst()

        for p  in self.particles:
            p.update(dt)
            if not (0 <= p.x <= self.map_width and 0 <= p.y <= self.map_height):
                p.life = 0

        for sp in self.sparks:    sp.update(dt)
        for f  in self._flash:    f.update(dt)

        self.particles = [p  for p  in self.particles if p.active]
        self.sparks    = [sp for sp in self.sparks    if sp.active]
        self._flash    = [f  for f  in self._flash    if f.active]

        if self._emit_t >= self._duration and not self.particles and not self.sparks:
            self.active = False

    def draw(self, surface, offset=(0, 0)):
        for f in self._flash: f.draw(surface, offset)

        for sp in self.sparks: sp.draw(surface, offset)

        for p in self.particles: p.draw(surface, offset)
