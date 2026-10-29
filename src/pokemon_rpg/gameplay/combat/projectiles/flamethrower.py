import math
import random

import pygame

from pokemon_rpg.gameplay.combat.projectiles.base import BaseProjectile, hit_rect

C_CORE = (239, 235, 166)
C_MID = (248, 166, 104)
C_OUTER = (212, 78, 43)

PIXEL_SIZE = 4

# Fraction of a particle's life above which it shows as yellow (color_stage 1).
# Higher = shorter yellow phase.
_YELLOW_THRESHOLD = 0.90


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

        self.color_stage = 1

    def _roll_color_stage(self):
        """1 (Core), 2 (Mid), or 3 (Outer) based on age, with a little flicker."""
        t = self.life / self.max_life
        flicker = random.uniform(-0.05, 0.05)
        if t > _YELLOW_THRESHOLD + flicker:
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
        self.color_stage = self._roll_color_stage()

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
    # One burst per 60 fps frame — the density the effect was tuned at
    BURST_INTERVAL = 1 / 60
    PARTICLES_PER_BURST = 6  # High particle count for solid volume
    SPARK_CHANCE = 0.7

    # Continuous stream: damage ticks per target rather than once per hit
    DAMAGE = 5
    DAMAGE_TICK = 0.3

    # Generous bound on how far a particle can travel from the nozzle
    _REACH = 260

    _EMIT_DURATION = 1.2  # seconds particles are emitted
    _MAX_PARTICLE_LIFE = 0.75  # upper bound of JetParticle.life
    # Freeze until the last yellow core particle fades
    FREEZE_DURATION = _EMIT_DURATION + _MAX_PARTICLE_LIFE * (1.0 - _YELLOW_THRESHOLD)

    def __init__(self, origin_x, origin_y, facing, duration=None, **kwargs):
        if duration is None:
            duration = self._EMIT_DURATION
        super().__init__(origin_x, origin_y, facing, speed=480, **kwargs)

        self._dir = math.atan2(self.velocity.y, self.velocity.x)
        self._speed = self.velocity.length()

        self._nx = float(origin_x)
        self._ny = float(origin_y)

        self._duration = duration
        self._emit_t = 0.0
        self._timer = 0.0
        self._hit_cooldowns = {}

        self.particles: list[JetParticle] = []
        self.sparks: list[EdgeSpark] = []

        self.rect = pygame.Rect(0, 0, 20, 20)
        self.rect.center = (self._nx, self._ny)

        # The nozzle never moves, so the walls the flame can reach are fixed.
        # Walls the nozzle clips from the side are skipped (same rule as
        # moving projectiles); a wall straight ahead blocks the flame.
        reach = self.rect.inflate(self._REACH * 2, self._REACH * 2)
        self._walls = [
            s.rect
            for s in self.collision_sprites
            if reach.colliderect(s.rect)
            and not (
                self.rect.colliderect(s.rect) and not self._is_ahead(self.rect, s.rect)
            )
        ]

    def _burst(self):
        for _ in range(self.PARTICLES_PER_BURST):
            self.particles.append(
                JetParticle(self._nx, self._ny, self._dir, self._speed)
            )
        if random.random() < self.SPARK_CHANCE:
            self.sparks.append(EdgeSpark(self._nx, self._ny, self._dir, self._speed))

    def _advance(self, dt):
        # Stationary emitter: active while it is still emitting
        self._emit_t += dt
        self._timer += dt
        while self._timer >= self.BURST_INTERVAL:
            self._timer -= self.BURST_INTERVAL
            self._burst()
        if self._emit_t >= self._duration:
            self._deactivate()

    def update_effects(self, dt):
        for p in self.particles:
            p.update(dt)
        for sp in self.sparks:
            sp.update(dt)

        if self._walls:
            probe = pygame.Rect(0, 0, 1, 1)
            for p in self.particles:
                probe.topleft = (p.x, p.y)
                if probe.collidelist(self._walls) != -1:
                    p.life = 0
            for sp in self.sparks:
                probe.topleft = (sp.x, sp.y)
                if probe.collidelist(self._walls) != -1:
                    sp.life = 0

        self.particles = [p for p in self.particles if p.active]
        self.sparks = [sp for sp in self.sparks if sp.active]

        self._damage_targets(dt)

    def _damage_targets(self, dt):
        for target in list(self._hit_cooldowns):
            self._hit_cooldowns[target] -= dt
            if self._hit_cooldowns[target] <= 0:
                del self._hit_cooldowns[target]

        for target in self.combat_sprites:
            if target in self._hit_cooldowns:
                continue
            box = hit_rect(target)
            if any(box.collidepoint(p.x, p.y) for p in self.particles):
                self.on_hit(target)
                self._hit_cooldowns[target] = self.DAMAGE_TICK

    def has_effects(self):
        return bool(self.particles or self.sparks)

    def draw(self, surface, offset=(0, 0)):

        # Base Layer: Dark Orange/Red (Large blocks)
        for p in self.particles:
            if p.color_stage == 3:
                p.draw(surface, C_OUTER, PIXEL_SIZE * 4, offset)

        # Sparks draw behind the core
        for sp in self.sparks:
            sp.draw(surface, offset)

        # Mid Layer: Peach/Orange (Medium blocks)
        for p in self.particles:
            if p.color_stage == 2:
                p.draw(surface, C_MID, PIXEL_SIZE * 3, offset)

        # Top Layer: Core White/Yellow (circular hot core)
        for p in self.particles:
            if p.color_stage == 1:
                sx = int((p.x - offset[0]) // PIXEL_SIZE) * PIXEL_SIZE + PIXEL_SIZE
                sy = int((p.y - offset[1]) // PIXEL_SIZE) * PIXEL_SIZE + PIXEL_SIZE
                pygame.draw.circle(surface, C_CORE, (sx, sy), PIXEL_SIZE)
