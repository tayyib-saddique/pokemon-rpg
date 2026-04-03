import pygame
import math
import random
from projectiles.base import BaseProjectile

B_RIM = (160, 220, 255)
B_SHINE = (230, 248, 255)
B_INNER = (80, 160, 240)
B_IRID = [
    (180, 200, 255),
    (200, 180, 255),
    (160, 240, 220),
    (200, 230, 255),
]


def draw_bubble(surface, cx, cy, r, irid_index=0, alpha_scale=1.0):
    if r < 1 or alpha_scale <= 0:
        return

    # Create a small transparent surface just for this bubble
    size = (r * 2 + 4, r * 2 + 4)
    bubble_surf = pygame.Surface(size, pygame.SRCALPHA)
    bx, by = r + 2, r + 2  # centre within the small surface

    # Inner fill — semi transparent
    pygame.draw.circle(bubble_surf, (*B_INNER, int(30 * alpha_scale)), (bx, by), r)

    # Outer rim
    pygame.draw.circle(bubble_surf, (*B_RIM, int(190 * alpha_scale)), (bx, by), r, 2)
    if r > 5:
        irid = B_IRID[irid_index % len(B_IRID)]
        pygame.draw.circle(
            bubble_surf, (*irid, int(150 * alpha_scale)), (bx, by), r - 1, 1
        )

    # Specular highlight
    if r >= 3:
        hx = bx - r // 3
        hy = by - r // 3
        hr = max(1, r // 4)
        pygame.draw.circle(
            bubble_surf, (*B_SHINE, int(230 * alpha_scale)), (hx, hy), hr
        )
        if r >= 6:
            pygame.draw.circle(
                bubble_surf,
                (*B_SHINE, int(128 * alpha_scale)),
                (hx + 2, hy + 2),
                max(1, hr - 1),
            )

    surface.blit(bubble_surf, (cx - r - 2, cy - r - 2))


class TrailBubble:
    def __init__(self, x, y, vx, vy, irid_index):
        self.x, self.y = float(x), float(y)

        perp = math.atan2(vy, vx) + math.pi / 2
        mag = random.uniform(5, 25) * random.choice((-1, 1))
        self.vx = math.cos(perp) * mag + vx * 0.04
        self.vy = math.sin(perp) * mag + vy * 0.04

        self.r = random.randint(3, 7)
        self.life = random.uniform(0.25, 0.55)
        self.max_life = self.life
        self.irid = irid_index
        self.wobble_phase = random.uniform(0, math.tau)
        self.wobble_speed = random.uniform(3, 6)

    def update(self, dt):
        self.wobble_phase += self.wobble_speed * dt
        w = math.sin(self.wobble_phase) * 0.4
        self.x += (self.vx + w) * dt
        self.y += (self.vy + w * 0.5) * dt
        self.life -= dt

    @property
    def active(self):
        return self.life > 0

    def draw(self, surface, offset=(0, 0)):
        draw_bubble(
            surface,
            int(self.x - offset[0]),
            int(self.y - offset[1]),
            self.r,
            self.irid,
            self.life / self.max_life,
        )


class BubbleBeam(BaseProjectile):
    TRAIL_INTERVAL = 0.04
    HEAD_RADII = [9, 6, 4]
    HEAD_OFFSETS = [(0, 0), (-5, 5), (6, -5)]

    def __init__(self, origin_x, origin_y, facing, **kwargs):
        super().__init__(origin_x, origin_y, facing, speed=340, **kwargs)

        self.trail = []
        self._trail_timer = 0
        self._wobble = 0.0
        self._irid_cycle = 0

        self.rect = pygame.Rect(0, 0, 18, 18)
        self.rect.center = self.pos

    def _spawn_trail(self):
        self._irid_cycle = (self._irid_cycle + 1) % len(B_IRID)
        # Spawn 1-2 trail bubbles slightly behind the head
        for _ in range(random.randint(1, 2)):
            self.trail.append(
                TrailBubble(
                    self.pos.x + random.uniform(-4, 4),
                    self.pos.y + random.uniform(-4, 4),
                    self.velocity.x,
                    self.velocity.y,
                    self._irid_cycle,
                )
            )

    def update(self, dt, *args, **kwargs):
        super().update(dt)
        self.rect.center = self.pos

        self._trail_timer += dt
        self._wobble += 2.5 * dt

        if self._trail_timer >= self.TRAIL_INTERVAL:
            self._trail_timer = 0.0
            self._spawn_trail()

        for b in self.trail:
            b.update(dt)
        self.trail = [b for b in self.trail if b.active]

    def draw(self, surface, offset=(0, 0)):
        # Trail bubbles drawn first (behind head)
        for b in self.trail:
            b.draw(surface, offset)

        # Head cluster — 3 bubbles with a gentle wobble offset
        for i, (base_dx, base_dy) in enumerate(self.HEAD_OFFSETS):
            r = self.HEAD_RADII[i]

            # Wobble each bubble slightly independently
            phase = self._wobble + i * (math.pi * 2 / 3)
            wdx = math.cos(phase) * 1.5
            wdy = math.sin(phase) * 1.5
            cx = int(self.pos.x - offset[0] + base_dx + wdx)
            cy = int(self.pos.y - offset[1] + base_dy + wdy)
            irid = (self._irid_cycle + i) % len(B_IRID)
            draw_bubble(surface, cx, cy, r, irid, 1.0)
