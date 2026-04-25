import pygame
import math
import random
from projectiles.base import BaseProjectile

BG = (18, 22, 30)
NOZZLE_OFFSET = 22

C_WHITE = (255, 255, 220)
C_YELLOW = (255, 235, 30)
C_ORANGE = (255, 115, 0)
C_RED = (210, 20, 0)
C_DARK = (80, 10, 0)


class JetParticle:
    def __init__(self, nx, ny, dir_angle, speed):
        # Starts as a highly compressed, high-speed beam
        spread = math.radians(random.uniform(-4, 4))
        self.angle = dir_angle + spread

        # Intense initial speed
        spd = speed * random.uniform(0.9, 1.4)

        self.x = float(nx)
        self.y = float(ny)

        self.vx = math.cos(self.angle) * spd
        self.vy = math.sin(self.angle) * spd

        # Longer lifespan to create a massive wall of fire
        self.life = random.uniform(0.35, 0.75)
        self.max_life = self.life

        # Violent outward expansion as the gas ignites and slows down
        perp_angle = dir_angle + (
            math.pi / 2 if random.random() > 0.5 else -math.pi / 2
        )
        self.expansion_rate = random.uniform(30, 110)
        self.exp_vx = math.cos(perp_angle) * self.expansion_rate
        self.exp_vy = math.sin(perp_angle) * self.expansion_rate

        # Heavy lift so the huge fireball rises at the end
        self.lift = random.uniform(-20, -60)

    @property
    def color_stage(self):
        """Returns 1 (Core), 2 (Mid), or 3 (Outer) based on age."""
        t = self.life / self.max_life
        flicker = random.uniform(-0.05, 0.05)
        if t > 0.75 + flicker:
            return 1
        elif t > 0.40 + flicker:
            return 2
        return 3

    def update(self, dt):
        # Extreme drag: hits a "wall" and billows outward
        drag = 1.0 - 3.5 * dt
        self.vx *= drag
        self.vy *= drag

        age = 1.0 - (self.life / self.max_life)

        # Exponential expansion makes it bloom outward suddenly, rather than linearly
        exp_curve = age**2

        self.x += (self.vx + self.exp_vx * exp_curve) * dt
        self.y += (self.vy + self.exp_vy * exp_curve + self.lift * age) * dt
        self.life -= dt

    @property
    def active(self):
        return self.life > 0

    def draw(self, surface, color, size, offset=(0, 0)):
        sx = int((self.x - offset[0]) // PIXEL_SIZE) * PIXEL_SIZE
        sy = int((self.y - offset[1]) // PIXEL_SIZE) * PIXEL_SIZE
        pygame.draw.rect(surface, color, (sx, sy, size, size))


class EdgeSpark:
    def __init__(self, x, y, dir_angle, beam_speed):
        side = random.choice((-1, 1))
        kick = dir_angle + math.pi / 4.5 * side + math.radians(random.uniform(-8, 8))
        spd = beam_speed * random.uniform(0.4, 0.8)

        self.x = float(x)
        self.y = float(y)
        self.vx = math.cos(kick) * spd + math.cos(dir_angle) * beam_speed * 0.4
        self.vy = math.sin(kick) * spd + math.sin(dir_angle) * beam_speed * 0.4
        self.life = random.uniform(0.15, 0.35)
        self.max_life = self.life

    def update(self, dt):
        self.vx *= 1.0 - 2.0 * dt
        self.vy *= 1.0 - 2.0 * dt
        self.vy += 50 * dt  # Gravity
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    @property
    def active(self):
        return self.life > 0

    def draw(self, surface, offset=(0, 0)):
        t = self.life / self.max_life
        col = C_OUTER if t < 0.4 else C_MID
        sx = int((self.x - offset[0]) // PIXEL_SIZE) * PIXEL_SIZE
        sy = int((self.y - offset[1]) // PIXEL_SIZE) * PIXEL_SIZE
        pygame.draw.rect(surface, col, (sx, sy, PIXEL_SIZE, PIXEL_SIZE))


class Flamethrower(BaseProjectile):
    BURST_INTERVAL = 0.008  # Extremely fast burst rate for density
    PARTICLES_PER_BURST = 6  # High particle count for solid volume
    SPARK_CHANCE = 0.7

    _EMIT_OFFSET = {
        "right": (8, -4),
        "left": (-8, -4),
        "down": (0, 18),
        "up": (0, -8),
    }

    def __init__(self, origin_x, origin_y, facing, duration=1.2, **kwargs):
        # Increased speed significantly for that high-pressure blast
        super().__init__(origin_x, origin_y, facing, speed=480, **kwargs)

        self._dir = math.atan2(self.velocity.y, self.velocity.x)
        self._speed = self.velocity.length()

        ox, oy = self._EMIT_OFFSET.get(facing, (0, 0))
        self._nx = float(origin_x) + math.cos(self._dir) * 4 + ox
        self._ny = float(origin_y) + math.sin(self._dir) * 4 + oy

        self._duration = duration
        self._emit_t = 0.0
        self._timer = 0.0

        self.particles: list[JetParticle] = []
        self.sparks: list[EdgeSpark] = []

        self.rect = pygame.Rect(0, 0, 20, 20)
        self.rect.center = (self._nx, self._ny)

    def _burst(self):
        for _ in range(self.PARTICLES_PER_BURST):
            self.particles.append(
                JetParticle(self._nx, self._ny, self._dir, self._speed)
            )
        if random.random() < self.SPARK_CHANCE:
            self.sparks.append(EdgeSpark(self._nx, self._ny, self._dir, self._speed))

    def update(self, dt, *args, **kwargs):
        if hasattr(self, "rect"):
            # Update rect position to follow origin if firing while moving
            self.rect.center = (self._nx, self._ny)
            for sprite in getattr(self, "collision_sprites", []):
                if self.rect.colliderect(sprite.rect):
                    self.active = False
                    return

        self._timer += dt

        if self._emit_t < self._duration:
            self._emit_t += dt
            if self._timer >= self.BURST_INTERVAL:
                self._timer = 0.0
                self._burst()

        for p in self.particles:
            p.update(dt)

        for sp in self.sparks:
            sp.update(dt)

        self.particles = [p for p in self.particles if p.active]
        self.sparks = [sp for sp in self.sparks if sp.active]

        if self._emit_t >= self._duration and not self.particles and not self.sparks:
            self.active = False

    def draw(self, surface, offset=(0, 0)):
        # LAYERED DRAWING: This forces the particles to look like a solid mass

        # 1. Base Layer: Dark Orange/Red (Large blocks)
        for p in self.particles:
            if p.color_stage == 3:
                p.draw(surface, C_OUTER, PIXEL_SIZE * 4, offset)

        # Sparks draw behind the core
        for sp in self.sparks:
            sp.draw(surface, offset)

        # 2. Mid Layer: Peach/Orange (Medium blocks)
        for p in self.particles:
            if p.color_stage == 2:
                p.draw(surface, C_MID, PIXEL_SIZE * 3, offset)

        # 3. Top Layer: Core White/Yellow (circular hot core)
        for p in self.particles:
            if p.color_stage == 1:
                sx = int((p.x - offset[0]) // PIXEL_SIZE) * PIXEL_SIZE + PIXEL_SIZE
                sy = int((p.y - offset[1]) // PIXEL_SIZE) * PIXEL_SIZE + PIXEL_SIZE
                pygame.draw.circle(surface, C_CORE, (sx, sy), PIXEL_SIZE)
